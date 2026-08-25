import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
django.setup()

from django.utils.timesince import timesince
from users.models import GuestFavorite
from notifications.models import UserDevice, NotificationLog

def run_diagnostics(guest_id):
    print("=" * 60)
    print(f"🔍 ScoreLivePRO Inbox Diagnostics for Guest: {guest_id}")
    print("=" * 60)

    # 1. Check GuestFavorite record
    guest_fav = GuestFavorite.objects.filter(device_id=guest_id).first()
    if not guest_fav:
        print(f"❌ WARNING: No GuestFavorite record found for device_id '{guest_id}'!")
        print("   This means the guest has not saved any favorites on the backend.")
        print("   Verify if your mobile app is successfully calling the POST favorites API.")
        return

    print("✅ GuestFavorite record found!")
    fav_teams = list(guest_fav.favorite_teams.all())
    fav_leagues = list(guest_fav.favorite_leagues.all())
    fav_fixtures = list(guest_fav.favorite_fixtures.all())

    print(f"   - Favorite Teams: {[t.name for t in fav_teams]} (IDs: {[t.id for t in fav_teams]})")
    print(f"   - Favorite Leagues: {[l.name for l in fav_leagues]} (IDs: {[l.id for l in fav_leagues]})")
    print(f"   - Favorite Matches: {[f.id for f in fav_fixtures]} (IDs: {[f.id for f in fav_fixtures]})")

    # 2. Check UserDevice registrations
    devices = UserDevice.objects.filter(guest_id=guest_id)
    print(f"\n📱 Registered Devices for Guest ID ({devices.count()} found):")
    for d in devices:
        print(f"   - ID: {d.id} | Lang: {d.language} | Active: {d.active} | Token: {d.registration_id[:20]}...")

    # 3. Build Topics List (simulating NotificationInboxView)
    topics = [f"guest_{guest_id}"]
    for t in fav_teams:
        topics.append(f"team_{t.id}")
    for l in fav_leagues:
        topics.append(f"league_{l.id}")
    for f in fav_fixtures:
        topics.append(f"match_{f.id}")
    topics.append("global")

    print(f"\n📂 Topics List built for inbox query:")
    print(f"   {topics}")

    # 4. Query NotificationLog for these topics
    logs = NotificationLog.objects.filter(topic__in=topics)
    print(f"\n📋 Inbox Notification Logs ({logs.count()} total matching):")
    if logs.exists():
        for log in logs[:10]:
            print(f"   - [{log.event_type}] Topic: {log.topic} | Title: {log.title} | Status: {log.status} | Created: {log.created_at} ({timesince(log.created_at)} ago)")
        if logs.count() > 10:
            print(f"   ... and {logs.count() - 10} more.")
    else:
        print("   ❌ No notifications found matching these topics in the database.")

    # 5. Check other sports notifications in DB to see if logging is working
    recent_sports_logs = NotificationLog.objects.exclude(topic="global").exclude(topic__startswith="guest_").exclude(topic__startswith="user_")
    print(f"\n📊 Total other sports notifications (team/match/league) in DB: {recent_sports_logs.count()}")
    if recent_sports_logs.exists():
        print("   Most recent 5 logged sports notifications:")
        for log in recent_sports_logs[:5]:
            print(f"   - [{log.event_type}] Topic: {log.topic} | Title: {log.title} | Status: {log.status} | Created: {log.created_at}")
    else:
        print("   ❌ No other sports notifications logged in the DB at all.")

    print("\n" + "=" * 60)
    print("💡 DIAGNOSIS SUMMARY:")
    if not logs.exists():
        if not recent_sports_logs.exists():
            print("👉 No sports notifications are being logged in your database. Ensure that the Celery workers are running and sending notifications through the backend's NotificationService.")
        else:
            print("👉 Sports notifications are being logged in the DB, but they do not match any topics this guest is following. Ensure the guest is following the correct matches/teams/leagues on the backend.")
    else:
        print("👉 Notifications exist in the DB for the topics this guest follows. If they are not appearing in the app, verify if the guest_id query parameter is being passed correctly, or if there is an issue with the client-side API parsing.")
    print("=" * 60)

if __name__ == "__main__":
    guest = "7a54d8fb-a182-4477-a82b-0d4cd1ba25eb"
    if len(sys.argv) > 1:
        guest = sys.argv[1]
    run_diagnostics(guest)
