# ScoreLivePRO Backend Architecture & Notification Engine Specification

**Document Version:** 2.4.1  
**Date:** September 2026  
**Status:** Production Verified  
**Target Systems:** Django REST Framework (Python 3.11+), Celery 5.x, Redis 7, Google Firebase Cloud Messaging (FCM HTTP v1 / Topics), PostgreSQL 15, Flutter Client (`v2scorelivepro`)

---

## 1. Executive System Overview

The ScoreLivePRO backend functions as a high-throughput, real-time sports synchronization and push notification engine. It ingests live football data from commercial REST APIs (API-Football / API-Sports), normalizes statuses across 16 FIFA states, broadcasts live score streams over WebSockets via Django Channels, and dispatches localized push notifications to iOS and Android devices via Google Firebase Cloud Messaging (FCM).

```
                      ┌────────────────────────────────────────┐
                      │ Upstream Provider: API-Football (REST) │
                      └───────────────────┬────────────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────────┐
                  │ 15s Ticker: /fixtures?live=all                    │
                  │ 45s Events: /fixtures/events?fixture={id}         │
                  │ 60s Stats:  /fixtures/statistics?fixture={id}     │
                  │ 15m Lineups: /fixtures/lineups?fixture={id}       │
                  └───────────────────────┬───────────────────────────┘
                                          ▼
                      ┌────────────────────────────────────────┐
                      │  Celery High-Priority Worker Queue     │
                      │  - Redis SETNX Distributed Locking     │
                      │  - Monotonic Status Guards (FT locked) │
                      │  - Event Diffing & Deduplication Cache │
                      └───────────────────┬────────────────────┘
                                          │
            ┌─────────────────────────────┴─────────────────────────────┐
            ▼                                                           ▼
┌───────────────────────┐                                   ┌───────────────────────┐
│ Django Channels (WS)  │                                   │ Firebase Admin SDK    │
│ group_send:           │                                   │ Concurrent Fanout (7) │
│ "live_scores"         │                                   │ /topics/match_{id}_it │
└───────────┬───────────┘                                   └───────────┬───────────┘
            │                                                           │
            ▼                                                           ▼
┌───────────────────────┐                                   ┌───────────────────────┐
│ WebSockets (Flutter)  │                                   │ Apple APNs / Google   │
│ UI Live Updates (<1s) │                                   │ FCM Push Delivery     │
└───────────────────────┘                                   └───────────────────────┘
```

---

## 2. Real-Time Task Architecture & Celery Beat Schedule

All live data ingestion is managed asynchronously by Celery workers decoupled from HTTP request-response cycles. Tasks are partitioned into two priority queues:
* `high_priority`: Live tickers, events, statistics, lineups, kickoff reminders, and scheduled push alerts.
* `celery` (Default): Maintenance, standings, H2H warmup, daily league schedules, and background reconciliation.

### 2.1. Task Routing Configuration (`config/celery.py`)

```python
app.conf.task_default_queue = 'celery'
app.conf.task_routes = {
    # High-Priority Real-Time Tasks & Notifications
    'sports.tasks.update_live_fixtures': {'queue': 'high_priority'},
    'sports.tasks.fetch_live_events': {'queue': 'high_priority'},
    'sports.tasks.fetch_live_statistics': {'queue': 'high_priority'},
    'sports.tasks.fetch_lineups_near_kickoff': {'queue': 'high_priority'},
    'sports.tasks.check_upcoming_matches_and_notify': {'queue': 'high_priority'},
    'sports.tasks.process_scheduled_notifications': {'queue': 'high_priority'},
    'notifications.tasks.*': {'queue': 'high_priority'},
    
    # Standard Maintenance & Background Sync Tasks
    'sports.tasks.fetch_upcoming_fixtures': {'queue': 'celery'},
    'sports.tasks.daily_maintenance_workflow': {'queue': 'celery'},
    'sports.tasks.warmup_upcoming_h2h': {'queue': 'celery'},
    'sports.tasks.fetch_standings_hourly': {'queue': 'celery'},
    'sports.tasks.cleanup_stale_live_fixtures': {'queue': 'celery'},
    'sports.tasks.reconcile_stuck_suspended_fixtures': {'queue': 'celery'},
    'sports.tasks.fetch_teams_for_active_leagues': {'queue': 'celery'},
    'sports.tasks.notify_daily_league_schedule': {'queue': 'celery'},
}
```

### 2.2. Celery Beat Schedules

| Task Name | Interval | Queue | Description |
| :--- | :--- | :--- | :--- |
| `update_live_fixtures` | **15.0 seconds** | `high_priority` | Polls `/fixtures?live=all`, saves match states, triggers goal/whistle alerts, and broadcasts to Channel Layer. |
| `fetch_live_events` | **45.0 seconds** | `high_priority` | Polls `/fixtures/events` for matches with followers, diffs cards/subs/VAR, and triggers push alerts. |
| `fetch_live_statistics` | **60.0 seconds** | `high_priority` | Refreshes possession, shots, corners, and fouls for active live fixtures. |
| `fetch_lineups_near_kickoff` | **15 minutes** | `high_priority` | Polls confirmed starting XI lineups 45–60 min before kickoff; notifies followers. |
| `process_scheduled_notifications` | **60.0 seconds** | `high_priority` | Dispatches admin-scheduled marketing or custom alerts. |
| `check_upcoming_matches_and_notify` | **Every 15 mins** | `high_priority` | Sends pre-match reminders 15 minutes before scheduled kickoff. |
| `daily_maintenance_workflow` | **Daily 03:00 AM** | `celery` | Sequential update chain: Countries → Seasons → Leagues → Teams → Schedule. |
| `warmup_upcoming_h2h` | **Daily 04:30 AM** | `celery` | Warms up Head-to-Head cache for all matches scheduled in the next 48 hours. |
| `notify_daily_league_schedule` | **Daily 08:00 AM** | `celery` | Dispatches daily match counts and schedules for followed leagues. |
| `fetch_standings_hourly` | **Hourly (:00)** | `celery` | Refreshes league standings and points tables. |
| `cleanup_stale_live_fixtures` | **Every 30 mins** | `celery` | Reconciles zombie fixtures stuck in live status for > 4 hours. |
| `reconcile_stuck_suspended_fixtures` | **Every 10 mins** | `celery` | Verifies rescheduled/suspended fixtures against upstream calendar. |

---

## 3. Concurrency Protection & Monotonic Integrity Guards

### 3.1. Distributed Redis Locking (`SETNX`)

To prevent worker concurrency races or duplicate API polling under high event volume, every critical task is protected by atomic Redis locks:

```python
def acquire_lock(lock_id, expire=60):
    """
    Attempts to acquire an atomic distributed lock using Redis SETNX.
    Returns True if lock acquired, False if already locked.
    """
    try:
        r = get_redis_client()
        # Atomic SET with NX=True ensures only one worker succeeds
        return bool(r.set(lock_id, "LOCKED", nx=True, ex=expire))
    except Exception as e:
        print(f"⚠️ REDIS LOCK ERROR: {e}")
        return True # Fail open to prevent permanent worker stall
```

* `task-lock-live-updates`: Expires in **15 seconds** (ticker loop).
* `task-lock-live-events`: Expires in **40 seconds** (detailed events).
* `task-lock-kickoff-lineups`: Expires in **300 seconds** (lineup polling).
* `task-lock-stats-update`: Expires in **60 seconds** (live statistics).
* `task-lock-standings-hourly`: Expires in **600 seconds** (standings).

### 3.2. Monotonic Status Guard (Prevents Post-Match Regressions)

A recurring problem in commercial sports APIs is that finished matches (`FT`, `AET`, `PEN`, `ABD`, `AWD`, `WO`) occasionally get temporarily omitted from live feeds or reported with stale in-play statuses (`2H`, `HT`) during API server caching hiccups.

To prevent finished matches from reverting backwards on user screens:

```python
# --- MONOTONIC STATUS GUARD ---
# A finished match (FT, AET, PEN, ABD, AWD, WO) must never regress to an in-play (2H, 1H, HT) or pre-match (NS) status
if fixture_exists and old_status in Fixture.FINISHED_STATUSES:
    if new_status not in Fixture.FINISHED_STATUSES:
        print(f"🛡️ [MONOTONIC GUARD] Prevented status regression for Match {fixture_id}: attempted {old_status} -> {new_status}")
        new_status = old_status
        status_data['short'] = old_status
        status_data['long'] = existing_fixture.status_long
        status_data['elapsed'] = existing_fixture.elapsed or 90
        status_data['extra'] = existing_fixture.extra
        g = existing_fixture.goals or g
        s = existing_fixture.score or s
```

---

## 4. Push Notification Engine Architecture

### 4.1. 5-Tier Hierarchical Subscription Model

Notifications are sent via Google Firebase Topics rather than mass device token loops. This guarantees sub-second dispatch regardless of whether 100 or 1,000,000 users follow a match.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Topic Subscription Layers                       │
├───────────────────┬───────────────────────────────────┬────────────────┤
│ Layer             │ Topic Format                      │ Fanned-Out By  │
├───────────────────┼───────────────────────────────────┼────────────────┤
│ 1. Match Layer    │ `/topics/match_{fixture_id}_{lang}`│ 7 Languages    │
│ 2. Home Team      │ `/topics/team_{home_id}_{lang}`   │ 7 Languages    │
│ 3. Away Team      │ `/topics/team_{away_id}_{lang}`   │ 7 Languages    │
│ 4. League Layer   │ `/topics/league_{league_id}_{lang}`│ 7 Languages   │
│ 5. Global Layer   │ `/topics/global_{lang}`           │ 7 Languages    │
│ Direct Inbox      │ `/topics/user_{user_id}`          │ Profile Locale │
└───────────────────┴───────────────────────────────────┴────────────────┘
```

> **Why Users Receive Alerts for Unstarred Matches:**  
> If a user favorited **River Plate** or the **Argentine Primera División**, they are subscribed to `team_435_it` and `league_128_it`. When River Plate plays Huracán, the backend dispatches to the team and league topics as well as the match topic. In the notification payload, the mobile app receives:
> `data["reason"] = "Following River Plate"` or `"Following Argentine Primera"`.

---

### 4.2. Multi-Language Concurrent Fanout

The engine supports 7 official languages: `en` (English), `es` (Spanish), `fr` (French), `de` (German), `it` (Italian), `pt` (Portuguese), and `tr` (Turkish).

When an alert is triggered, it is translated and fanned out concurrently using a `ThreadPoolExecutor` to eliminate sequential network latency:

```python
# Fan out to all supported languages concurrently to eliminate multi-second HTTP latency
from concurrent.futures import ThreadPoolExecutor

def _send_lang(lang):
    t_title, t_body = translate_notification(title, body, event_type, lang)
    return NotificationService.send_push_to_topic(
        f"{topic}_{lang}", t_title, t_body, data, event_type, is_internal=True
    )

langs = ['en', 'es', 'fr', 'de', 'it', 'pt', 'tr']
with ThreadPoolExecutor(max_workers=len(langs)) as executor:
    list(executor.map(_send_lang, langs))
```

---

### 4.3. Complete Match Event Mapping & Triggers

All incidents are evaluated inside `save_fixture_from_api` and `update_fixture_details(type='events')`:

| Event Type | DB / API Trigger Condition | Dispatched Method | Payload `event_type` |
| :--- | :--- | :--- | :--- |
| **⚽ Goal** | `new_goals > old_goals` | `NotificationService.send_goal_alert` | `GOAL` |
| **❌ VAR Disallowed Goal** | `new_goals < old_goals` (Score decreased) | `NotificationService.send_disallowed_goal_alert` | `DISALLOWED_GOAL` |
| **🟨 Yellow Card** | New `Card` event with detail `'Yellow Card'` | `NotificationService.send_card_alert` | `CARD` |
| **🟥 Red Card** | New `Card` event with detail `'Red Card'` | `NotificationService.send_card_alert` | `CARD` |
| **🔄 Substitution** | New `subst` event in `events[]` | `NotificationService.send_substitution_alert` | `SUBSTITUTION` |
| **🖥️ VAR Review** | New `Var` event in `events[]` | `NotificationService.send_var_alert` | `VAR` |
| **⏱️ Kickoff Whistle (1H)**| `old_status in ['NS','TBD']` and `new_status in ['1H','LIVE']` | `NotificationService.send_kickoff_alert` | `KICKOFF` |
| **⏸️ Half-Time (HT)** | `old_status != 'HT'` and `new_status == 'HT'` | `NotificationService.send_half_time_alert` | `HALF_TIME` |
| **▶️ 2nd Half Kickoff (2H)**| `old_status == 'HT'` and `new_status == '2H'` | `NotificationService.send_second_half_alert` | `SECOND_HALF` |
| **⏳ Extra Time (ET)** | `old_status in ['2H','FT','BT']` and `new_status == 'ET'` | `NotificationService.send_extra_time_alert` | `EXTRA_TIME` |
| **🎯 Penalty Shootout (P)** | `old_status in ['ET','BT']` and `new_status == 'P'` | `NotificationService.send_penalty_shootout_alert` | `PENALTY_SHOOTOUT` |
| **❌ Missed Penalty** | New `Goal` event with detail `'Missed Penalty'` | `NotificationService.send_missed_penalty_alert` | `MISSED_PENALTY` |
| **🤦 Own Goal** | New `Goal` event with detail `'Own Goal'` | `NotificationService.send_own_goal_alert` | `OWN_GOAL` |
| **🏁 Match Finished (FT)** | `old_status != 'FT'` and `new_status in ['FT','AET','PEN']` | `NotificationService.send_match_result_alert` | `FULL_TIME` |
| **⚠️ Disruption / Postponed**| Status changes to `PST`, `SUSP`, `INT`, `ABD`, `CANC` | `NotificationService.send_match_disruption_alert`| `POSTPONED`, `SUSPENDED`, etc. |
| **📋 Official Lineups** | New starting XI saved in `FixtureLineup` | `NotificationService.send_lineup_alert` | `LINEUPS` |
| **⏰ Pre-Match Reminder** | Match kickoff within 15 mins (scheduled) | `NotificationService.send_match_reminder` | `MATCH_START` |
| **📅 Daily League Update** | Scheduled daily morning dispatch | `NotificationService.send_league_daily_update` | `DAILY_SCHEDULE` |

---

### 4.4. Event Deduplication & Idempotency Filter

To ensure workers never broadcast duplicate goals or cards during network retries:

1. **Redis Atomic Key:**
   ```python
   dedup_key = f"notif_dedup:{event_type}:{topic}:{m_id}:{sub_id}"
   if not r.set(dedup_key, "1", nx=True, ex=7200):
       return False # Already sent within the last 2 hours
   ```
2. **Database Verification:**
   Before dispatching, `NotificationLog` is queried to confirm the exact score, card, or substitution has not been logged previously for this match.
3. **APNs Collapse-ID & Android Collapse-Key:**
   Payloads include collapse headers so that if a device is offline, subsequent match events replace earlier ones in the phone's notification tray rather than stacking outdated information:

| Event Type | Production Collapse Key Format | Purpose |
| :--- | :--- | :--- |
| **Goal** | `match_{id}_goal` | Replaces earlier scorelines with latest score |
| **Half-Time** | `match_{id}_ht` | Replaces in-play status |
| **Full-Time** | `match_{id}_ft` | Final full-time result banner |
| **Official Lineups**| `match_{id}_lineups` | Lineup confirmation banner |
| **Pre-Match / 1H** | `match_{id}_kickoff` | Kickoff whistle alert |
| **2nd Half Kickoff**| `match_{id}_2h` | Second half resumption |
| **Extra Time** | `match_{id}_et` | Extra time alert |
| **Penalties** | `match_{id}_penalties` | Penalty shootout alert |
| **Disruptions** | `match_{id}_status` | Postponed, suspended, interrupted |
| **Missed Penalty** | `match_{id}_missedpen_{elapsed}` | Specific missed penalty event |
| **Own Goal** | `match_{id}_owngoal_{elapsed}` | Specific own goal event |

---

## 5. Device Token Management & Multi-Device Sync

### 5.1. The Data Models

#### `UserDevice` (`apps/notifications/models.py`)
```python
class UserDevice(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'), ('es', 'Spanish'), ('fr', 'French'),
        ('de', 'German'), ('it', 'Italian'), ('pt', 'Portuguese'), ('tr', 'Turkish'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='devices', null=True, blank=True)
    guest_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    registration_id = models.CharField(max_length=512, unique=True)
    type = models.CharField(max_length=10, choices=[('ios', 'iOS'), ('android', 'Android'), ('web', 'Web')], default='android')
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Automatically synchronize owner's FanProfile language preference
        if self.user and self.active:
            try:
                from users.models import FanProfile
                profile, _ = FanProfile.objects.get_or_create(user=self.user)
                if profile.language != self.language:
                    profile.language = self.language
                    profile.save(update_fields=['language'])
            except Exception:
                pass
        super().save(*args, **kwargs)
```

#### `GuestFavorite` (`apps/users/models.py`)
```python
class GuestFavorite(models.Model):
    device_id = models.CharField(max_length=255, unique=True, db_index=True) # Maps to guest UUID
    favorite_teams = models.ManyToManyField('sports.Team', blank=True, related_name='guest_favorites')
    favorite_leagues = models.ManyToManyField('sports.League', blank=True, related_name='guest_favorites')
    favorite_fixtures = models.ManyToManyField('sports.Fixture', blank=True, related_name='guest_favorites')
    last_inbox_check = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

---

### 5.2. Registration Flow (`POST /api/notifications/devices/register/`)

```
[Flutter Client: Startup / Token Refresh]
                  │
                  ▼
[POST /api/notifications/devices/register/]
Headers: Content-Type: application/json
Body: {
  "registration_id": "<FCM_TOKEN>",
  "type": "ios" | "android",
  "language": "it",
  "guest_id": "<DEVICE_UUID>"  (required for anonymous users)
}
                  │
                  ▼
[Backend: FCMDeviceView]
  • Updates registration_id, type, language, active=True
  • If Language changed: calls update_device_topic_subscriptions_task
  • If New Device: calls sync_device_subscriptions_task
```

### 5.3. Topic Synchronization Routine (`sync_device_subscriptions`)

Whenever a device registers, changes language, or logs in, Celery synchronizes its FCM token with its complete favorites catalog:

```python
def sync_device_subscriptions(device):
    # 1. Determine active language (User Profile > Device Language > 'en')
    user = device.user
    guest_id = device.guest_id
    lang = (user.fan_profile.language if user and hasattr(user, 'fan_profile') and user.fan_profile.language 
            else device.language or 'en')
    
    # 2. Collect all followed Team, League, and Fixture IDs
    team_ids, league_ids, fixture_ids = get_user_or_guest_favorites(device)
    
    # 3. Subscribe to active language topics & purge stale language topics
    languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'tr']
    other_langs = [l for l in languages if l != lang]

    for tid in team_ids:
        NotificationService.subscribe_tokens_to_topic([device.registration_id], f"team_{tid}_{lang}")
        NotificationService.unsubscribe_tokens_from_topic([device.registration_id], f"team_{tid}")
        for ol in other_langs:
            NotificationService.unsubscribe_tokens_from_topic([device.registration_id], f"team_{tid}_{ol}")

    for fid in fixture_ids:
        # Subscribe localized match and legacy fixture topics
        for prefix in ['match', 'fixture']:
            NotificationService.subscribe_tokens_to_topic([device.registration_id], f"{prefix}_{fid}_{lang}")
            NotificationService.unsubscribe_tokens_from_topic([device.registration_id], f"{prefix}_{fid}")
            for ol in other_langs:
                NotificationService.unsubscribe_tokens_from_topic([device.registration_id], f"{prefix}_{fid}_{ol}")
```

---

## 6. Forensic Breakdown: The 3-Device Discrepancy

During multi-device testing (e.g., 1 Android phone and 2 iPhones), a goal alert arrived on only 1 iPhone. Here is the technical explanation of why devices diverge:

### 1. Guest Mode Isolation
* Each unauthenticated device has its own `guest_id` UUID generated locally in Flutter secure storage.
* Favoriting a match on iPhone 1 updates `GuestFavorite(device_id="uuid_iphone1")`.
* It does **not** update iPhone 2 (`uuid_iphone2`) or Android (`uuid_android3`).
* To test simultaneously across devices, either:
  * Log in with the **same email user account** on all three devices, or
  * Star the match individually on each device.

### 2. The Language Guard Filter (`shouldProcessMessage`)
* If iPhone 1 is set to Italian (`it`), its token subscribes to `match_123_it`.
* If iPhone 2 or Android has its system locale set to English (`en`), but was subscribed to `match_123_it` during earlier testing:
  The Flutter client executes this check in `firebase_service.dart`:
  ```dart
  if (topicName.endsWith('_$lang') && lang != currentAppLang) {
    debugPrint('🛡️ [FCM] Dropping notification: topic language "$lang" != user language "$currentAppLang"');
    return false; // DROPPED SILENTLY
  }
  ```
  The push packet arrives at the phone, but Flutter's language guard drops it before displaying the banner.

### 3. Android 13+ Permissions & OEM Battery Optimization
* On Android 13+ (API 33+), the `POST_NOTIFICATIONS` runtime permission must be granted.
* On OEM Android devices (Xiaomi MIUI, Samsung OneUI, OnePlus, Oppo), "Doze Mode" suspends Google Play Services background push sockets when the phone is locked, delaying delivery until the device wakes up or a maintenance window opens.

### 4. iOS APNs Handshake Latency
* Google Firebase cannot generate an FCM token on iOS until Apple's APNs server returns an APNs hardware token (`getAPNSToken()`).
* If iPhone 2 had network delay during cold-start or was set to "Scheduled Summary" in iOS Settings, token registration was delayed and was not yet in the backend database when the goal occurred.

---

## 7. The 6-Point Forensic Log Trail

Whenever an alert is processed, the backend records its forensic lifecycle:

```
Point 1: Provider Ingestion (API-Sports JSON payload)
         └─ Limitation: API-Football only supplies match elapsed (e.g. 41'), not wall-clock entry epoch.
Point 2: Backend Reception Timestamp
         └─ Recorded in Celery worker polling log (e.g. 2026-09-19T22:44:30.012Z).
Point 3: Celery Processing Duration
         └─ In-memory evaluation and Redis locking: < 15 milliseconds.
Point 4: Firebase Dispatch Timestamp
         └─ Recorded in NotificationLog.created_at (e.g. 2026-09-19T22:44:30.380Z).
Point 5: FCM Message ID & Topic
         └─ Returned by Firebase: projects/scorelivepro/messages/1726785873123456
         └─ Target Topic: /topics/match_1638771_it.
Point 6: Device Subscription State
         └─ Verified in UserDevice + GuestFavorite database tables.
```

---

## 8. Unfavoriting & Orphan Topic Cleanup Best Practices

### 8.1. The 60-Second Google Cloud Edge Propagation Window
When a user unfavorites a match, the backend calls `messaging.unsubscribe_from_topic()`. Google FCM returns HTTP 200 immediately. However, Google's worldwide distributed edge caching network takes **30 to 120 seconds** to invalidate cached topic subscriptions across all edge nodes. Notifications sent during this window may still reach the device.

### 8.2. Recommended Logout Hook for Mobile Client
When a user logs out, the mobile app should invoke `FirebaseMessaging.instance.deleteToken()`. This purges the hardware token from all Google Cloud topic mappings instantly and prevents "ghost" notifications from following the device across account switches.

---

## 9. Verification & Testing Commands

### 9.1. Run Unit Tests (Docker Production Environment)
```bash
# Verify both notification and sports test suites (47 tests)
docker compose exec web python manage.py test notifications sports
```

### 9.2. Run Unit Tests (Local Virtualenv Environment)
```bash
# Ensure apps/ is in PYTHONPATH and execute
python manage.py test notifications sports
```

### 9.3. Test Direct Celery Task Execution in Shell
```bash
docker compose exec web python manage.py shell -c "from sports.tasks import update_live_fixtures; print(update_live_fixtures())"
```

### 9.4. Send Direct Diagnostic Push via API
```bash
curl -X POST https://api.scorelivepro.it/api/notifications/test-push/ \
  -H "Content-Type: application/json" \
  -d '{
    "token": "all",
    "title": "⚽ Test Goal Notification",
    "body": "Testing multi-device synchronization",
    "event_type": "GOAL"
  }'
```

### 9.5. Check Active Devices & Subscriptions in Django Shell
```python
from notifications.models import UserDevice, NotificationLog
print("Active Devices:", UserDevice.objects.filter(active=True).count())
print("iOS Devices:", UserDevice.objects.filter(active=True, type='ios').count())
print("Android Devices:", UserDevice.objects.filter(active=True, type='android').count())
print("Total Sent Notifications:", NotificationLog.objects.filter(status='SENT').count())
```
