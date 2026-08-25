import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from users.models import GuestFavorite
from notifications.models import UserDevice, NotificationLog
from sports.models import Fixture, Team, League
from notifications.services import NotificationService
from rest_framework.test import APIRequestFactory
from notifications.views import NotificationInboxView

def run_local_test():
    print("=" * 60)
    print("🧪 Running Local Inbox Integration Test")
    print("=" * 60)

    # 1. Setup Test Data (Use existing sports data if available)
    print("1. Setting up mock sports data...")
    fixture = Fixture.objects.first()
    if fixture:
        home_team = fixture.home_team
        away_team = fixture.away_team
        league = fixture.league
        print(f"   Using existing fixture ID: {fixture.id} ({home_team.name} vs {away_team.name})")
    else:
        league, _ = League.objects.get_or_create(id=9999, defaults={'name': 'Test League', 'season_year': 2026})
        home_team, _ = Team.objects.get_or_create(id=9998, defaults={'name': 'Home Team'})
        away_team, _ = Team.objects.get_or_create(id=9997, defaults={'name': 'Away Team'})
        fixture, _ = Fixture.objects.get_or_create(
            id=999999,
            defaults={
                'league': league,
                'home_team': home_team,
                'away_team': away_team,
                'date': '2026-08-25T12:00:00Z',
                'status_short': 'NS'
            }
        )
        print(f"   Created mock fixture ID: {fixture.id} ({home_team.name} vs {away_team.name})")

    # 2. Register Guest & Favorites
    guest_id = "test_guest_inbox_12345"
    token = "test_device_token_abcde12345"
    
    print("\n2. Registering guest device and favorites...")
    # Register device
    device, _ = UserDevice.objects.update_or_create(
        registration_id=token,
        defaults={
            'guest_id': guest_id,
            'type': 'android',
            'language': 'en',
            'active': True
        }
    )
    # Add match to favorites
    guest_fav, _ = GuestFavorite.objects.get_or_create(device_id=guest_id)
    guest_fav.favorite_fixtures.add(fixture)
    
    print(f"   Registered Guest ID: {guest_id}")
    print(f"   Registered Device Token: {token}")
    print(f"   Added Fixture {fixture.id} to Guest favorites list.")

    # 3. Send Notification to Topic
    print("\n3. Dispatching goal notification to match topic...")
    title = f"⚽ Goal by {home_team.name}!"
    body = f"Current Score: {home_team.name} 1 - 0 {away_team.name}"
    data = {
        "type": "match",
        "event_type": "GOAL",
        "match_id": str(fixture.id),
        "team_id": str(home_team.id),
        "score": "1 - 0"
    }
    
    # We trigger send_push_to_topic. This should log the base topic to DB
    # and fanout to languages (which we mock/bypass by disabling FCM call if no credentials).
    # Since we are local, let's call it.
    try:
        # Temporarily mock ensure_firebase_initialized to bypass actual Firebase connection
        original_ensure = NotificationService.ensure_firebase_initialized
        NotificationService.ensure_firebase_initialized = lambda: None
        
        # Mock actual messaging.send to avoid external call
        import firebase_admin.messaging as messaging
        original_send = messaging.send
        messaging.send = lambda message, dry_run=False, app=None: "mock_fcm_message_id"
        original_subscribe = messaging.subscribe_to_topic
        messaging.subscribe_to_topic = lambda tokens, topic: None
        
        NotificationService.send_push_to_topic(
            topic=f"match_{fixture.id}",
            title=title,
            body=body,
            data=data,
            event_type='GOAL'
        )
        print("   Notification successfully fanned out and logged!")
    except Exception as e:
        print(f"   ❌ Error sending notification: {e}")
    finally:
        # Restore mock functions
        NotificationService.ensure_firebase_initialized = original_ensure
        messaging.send = original_send
        messaging.subscribe_to_topic = original_subscribe

    # 4. Query Inbox API View
    print("\n4. Querying the NotificationInboxView locally...")
    factory = APIRequestFactory()
    # Create request simulating GET /api/notifications/inbox/?guest_id=test_guest_inbox_12345
    request = factory.get(f'/api/notifications/inbox/?guest_id={guest_id}')
    
    # Instantiate view and set request/format
    view = NotificationInboxView.as_view()
    response = view(request)
    
    print(f"   Response Status Code: {response.status_code}")
    print(f"   Response Data Count: {len(response.data)}")
    
    # Check if our logged notification is in the response data
    found = False
    for item in response.data:
        if item.get('event_type') == 'GOAL' and str(item.get('data', {}).get('match_id')) == str(fixture.id):
            found = True
            print("   🎉 SUCCESS! The goal notification was found in the guest's inbox response:")
            print(f"      - Title: {item.get('title')}")
            print(f"      - Body: {item.get('body')}")
            print(f"      - Event Type: {item.get('event_type')}")
            break
            
    if not found:
        print("   ❌ FAILURE: The notification was NOT found in the inbox response.")

    print("=" * 60)

if __name__ == "__main__":
    run_local_test()
