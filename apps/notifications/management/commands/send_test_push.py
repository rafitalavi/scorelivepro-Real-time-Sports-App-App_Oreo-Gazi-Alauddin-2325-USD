from django.core.management.base import BaseCommand
from notifications.models import UserDevice
from notifications.services import NotificationService, translate_notification

class Command(BaseCommand):
    help = 'Sends test push notifications to all active devices in their preferred language'

    def add_arguments(self, parser):
        parser.add_argument('--title', type=str, default='⚽ Goal by Real Madrid!', help='English title template')
        parser.add_argument('--body', type=str, default='Current Score: Real Madrid 1 - 0 Barcelona', help='English body template')
        parser.add_argument('--event-type', type=str, default='GOAL', help='Event type (GOAL, FULL_TIME, LINEUPS, SCHEDULE)')
        parser.add_argument('--user-id', type=str, default=None, help='Target a specific User UUID')
        parser.add_argument('--email', type=str, default=None, help='Target a specific user by Email')
        parser.add_argument('--guest-id', type=str, default=None, help='Target a specific Guest ID')
        parser.add_argument('--match-id', type=str, default=None, help='Match ID for deep linking')
        parser.add_argument('--league-id', type=str, default=None, help='League ID for deep linking')
        parser.add_argument('--team-id', type=str, default=None, help='Team ID for deep linking')
        parser.add_argument('--player-id', type=str, default=None, help='Player ID for deep linking')
        parser.add_argument('--type', type=str, default=None, help='Override deep linking routing type')

    def handle(self, *args, **options):
        title = options['title']
        body = options['body']
        event_type = options['event_type']
        user_id = options['user_id']
        email = options['email']
        guest_id = options['guest_id']
        match_id = options['match_id']
        league_id = options['league_id']
        team_id = options['team_id']
        player_id = options['player_id']
        routing_type = options['type']

        devices = UserDevice.objects.filter(active=True)
        if user_id:
            devices = devices.filter(user_id=user_id)
        if email:
            devices = devices.filter(user__email=email)
        if guest_id:
            devices = devices.filter(guest_id=guest_id)

        if not devices.exists():
            self.stdout.write(self.style.WARNING("No matching active devices found in the database."))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {devices.count()} matching active devices. Sending test notifications..."))

        success_count = 0
        fail_count = 0

        # Construct data payload
        data_payload = {
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "event_type": event_type,
        }
        if routing_type:
            data_payload["type"] = routing_type
        if match_id:
            data_payload["match_id"] = str(match_id)
        if league_id:
            data_payload["league_id"] = str(league_id)
        if team_id:
            data_payload["team_id"] = str(team_id)
        if player_id:
            data_payload["player_id"] = str(player_id)

        for device in devices:
            t_title, t_body = translate_notification(title, body, event_type, device.language)
            res = NotificationService.send_push_to_token(
                device.registration_id,
                t_title,
                t_body,
                data=data_payload
            )

            owner = device.user.email if device.user else f"Guest ({device.guest_id})"
            if res.get("success"):
                success_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"[{device.language}] Sent successfully to {owner} (MsgID: {res.get('message_id')})"
                ))
            else:
                fail_count += 1
                self.stdout.write(self.style.ERROR(
                    f"[{device.language}] Failed to send to {owner}: {res.get('error')}"
                ))

        self.stdout.write(self.style.SUCCESS(
            f"Finished. Success: {success_count}, Failed: {fail_count}"
        ))


