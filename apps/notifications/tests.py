from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from .models import UserDevice, NotificationLog
from .services import translate_notification, update_device_topic_subscriptions
from .serializers import NotificationLogSerializer

User = get_user_model()

class NotificationLocalizationTests(TestCase):
    def test_translate_notification_goal(self):
        # English Goal alert: "⚽ Goal by PSG!" and "Current Score: PSG 2 - 1 Inter"
        title = "⚽ Goal by PSG!"
        body = "Current Score: PSG 2 - 1 Inter"
        
        # Test Spanish translation
        t_title, t_body = translate_notification(title, body, 'GOAL', 'es')
        self.assertEqual(t_title, "⚽ ¡Gol de PSG!")
        self.assertEqual(t_body, "Marcador actual: PSG 2 - 1 Inter")
        
        # Test Turkish translation
        t_title, t_body = translate_notification(title, body, 'GOAL', 'tr')
        self.assertEqual(t_title, "⚽ PSG Gol Attı!")
        self.assertEqual(t_body, "Mevcut Skor: PSG 2 - 1 Inter")

    def test_translate_notification_full_time(self):
        title = "🏁 Full Time"
        body = "Final Result: Real Madrid 3 - 0 Barcelona"
        
        # Test French translation
        t_title, t_body = translate_notification(title, body, 'FULL_TIME', 'fr')
        self.assertEqual(t_title, "🏁 Fin du match")
        self.assertEqual(t_body, "Résultat final : Real Madrid 3 - 0 Barcelona")

    def test_translate_notification_lineups(self):
        title = "📋 Lineups Released"
        body = "Starting XI is now available for Bayern vs Arsenal"
        
        # Test German translation
        t_title, t_body = translate_notification(title, body, 'LINEUPS', 'de')
        self.assertEqual(t_title, "📋 Aufstellungen bestätigt")
        self.assertEqual(t_body, "Die Startaufstellung für Bayern gegen Arsenal ist jetzt verfügbar")

    def test_translate_notification_schedule(self):
        title = "📅 Premier League Schedule"
        body = "There are 5 matches starting tomorrow in Premier League. Don't miss out!"
        
        # Test Italian translation
        t_title, t_body = translate_notification(title, body, 'SCHEDULE', 'it')
        self.assertEqual(t_title, "📅 Calendario Premier League")
        self.assertEqual(t_body, "Ci sono 5 partite domani in Premier League. Non perdere l'appuntamento!")

    def test_translate_notification_match_start(self):
        title = "⏳ Kickoff Soon"
        body = "Match starts in 15 mins: Chelsea vs Arsenal"
        
        # Test Italian translation
        t_title, t_body = translate_notification(title, body, 'MATCH_START', 'it')
        self.assertEqual(t_title, "⏳ Calcio d'inizio imminente")
        self.assertEqual(t_body, "La partita inizia tra 15 minuti: Chelsea vs Arsenal")

        # Test Spanish translation
        t_title, t_body = translate_notification(title, body, 'MATCH_START', 'es')
        self.assertEqual(t_title, "⏳ Empieza pronto")
        self.assertEqual(t_body, "El partido comienza en 15 minutos: Chelsea vs Arsenal")

    def test_translate_notification_card(self):
        # Yellow Card English: "🟨 Card for Messi (Inter)" and "Messi received a Yellow Card in the 45' minute."
        title = "🟨 Card for Messi (Inter)"
        body = "Messi received a Yellow Card in the 45' minute."
        t_title, t_body = translate_notification(title, body, 'CARD', 'es')
        self.assertEqual(t_title, "🟨 ¡Tarjeta amarilla para Messi (Inter)!")
        self.assertEqual(t_body, "Messi recibió una tarjeta en el minuto 45'.")

        # Red Card English
        title2 = "🟥 Card for Neymar (Inter)"
        body2 = "Neymar received a Red Card in the 88' minute."
        t_title2, t_body2 = translate_notification(title2, body2, 'CARD', 'tr')
        self.assertEqual(t_title2, "🟥 Neymar Kırmızı Kart Gördü (Inter)!")
        self.assertEqual(t_body2, "Neymar 88'. dakikada kart gördü.")

    def test_translate_notification_substitution(self):
        title = "🔄 Substitution for Inter"
        body = "In: Messi | Out: Neymar (75')"
        t_title, t_body = translate_notification(title, body, 'SUBSTITUTION', 'es')
        self.assertEqual(t_title, "🔄 Cambio en Inter")
        self.assertEqual(t_body, "Entra: Messi | Sale: Neymar (75')")

    def test_translate_notification_var(self):
        title = "🖥️ VAR Decision: Inter"
        body = "Goal Disallowed (34')"
        t_title, t_body = translate_notification(title, body, 'VAR', 'es')
        self.assertEqual(t_title, "🖥️ Decisión del VAR: Inter")
        self.assertEqual(t_body, "Goal Disallowed (34')")


class FCMDeviceLanguageAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="fan@example.com", password="password123")
        self.client.force_authenticate(user=self.user)
        # Get fan profile (automatically created by signal)
        self.profile = self.user.fan_profile

    def test_register_device_with_language(self):
        url = reverse('register-device')
        data = {
            "registration_id": "token_123_abc",
            "type": "android",
            "language": "es"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify language saved on device
        device = UserDevice.objects.get(registration_id="token_123_abc")
        self.assertEqual(device.language, "es")
        
        # Verify synced to User FanProfile
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.language, "es")

    def test_register_device_default_language(self):
        url = reverse('register-device')
        data = {
            "registration_id": "token_xyz_default",
            "type": "ios"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        device = UserDevice.objects.get(registration_id="token_xyz_default")
        self.assertEqual(device.language, "en")


class NotificationLogSerializerTranslationTests(TestCase):
    def test_serializer_translates_on_the_fly(self):
        log = NotificationLog.objects.create(
            topic="team_85",
            title="⚽ Goal by PSG!",
            body="Current Score: PSG 1 - 0 Inter",
            event_type="GOAL"
        )
        
        # Serialize with Spanish context
        serializer = NotificationLogSerializer(log, context={'language': 'es'})
        data = serializer.data
        self.assertEqual(data['title'], "⚽ ¡Gol de PSG!")
        self.assertEqual(data['body'], "Marcador actual: PSG 1 - 0 Inter")
        
        # Serialize with English context
        serializer_en = NotificationLogSerializer(log, context={'language': 'en'})
        data_en = serializer_en.data
        self.assertEqual(data_en['title'], "⚽ Goal by PSG!")


class FCMDataRoutingPayloadTests(TestCase):
    def test_send_push_to_token_data_payload_standardization(self):
        from .services import NotificationService
        # Test simulation send_push_to_token
        NotificationService.send_push_to_token(
            token="test_device_token",
            title="Goal Scored",
            body="PSG scored a goal",
            data={
                "match_id": 12345,
            }
        )
        log = NotificationLog.objects.last()
        self.assertIsNotNone(log)
        data = log.data
        self.assertEqual(data.get("click_action"), "FLUTTER_NOTIFICATION_CLICK")
        self.assertEqual(data.get("type"), "general")
        self.assertEqual(data.get("event_type"), "DEV_TEST")

    def test_send_goal_alert_data_payload(self):
        from .services import NotificationService
        NotificationService.send_goal_alert(
            scoring_team_name="PSG",
            home_team_name="PSG",
            away_team_name="Inter",
            score="1-0",
            home_team_id=85,
            away_team_id=86,
            match_id=999,
            league_id=10
        )
        
        logs = NotificationLog.objects.filter(topic="team_85")
        self.assertTrue(logs.exists())
        log = logs.last()
        
        self.assertEqual(log.data.get("click_action"), "FLUTTER_NOTIFICATION_CLICK")
        self.assertEqual(log.data.get("type"), "match")
        self.assertEqual(log.data.get("event_type"), "GOAL")
        self.assertEqual(log.data.get("match_id"), "999")
        self.assertEqual(log.data.get("team_id"), "85")

    def test_send_card_alert_data_payload(self):
        from .services import NotificationService
        NotificationService.send_card_alert(
            player_name="Messi",
            card_type="Yellow Card",
            team_name="Inter",
            team_id=86,
            match_id=999,
            elapsed_time=45,
            league_id=10
        )
        logs = NotificationLog.objects.filter(topic="match_999", event_type="CARD")
        self.assertTrue(logs.exists())
        log = logs.last()
        self.assertEqual(log.data.get("click_action"), "FLUTTER_NOTIFICATION_CLICK")
        self.assertEqual(log.data.get("type"), "match")
        self.assertEqual(log.data.get("event_type"), "CARD")
        self.assertEqual(log.data.get("player_name"), "Messi")
        self.assertEqual(log.data.get("card_type"), "Yellow Card")
        self.assertEqual(log.data.get("elapsed"), "45")

    def test_send_substitution_alert_data_payload(self):
        from .services import NotificationService
        NotificationService.send_substitution_alert(
            player_in="Mbappe",
            player_out="Vinicius",
            team_name="Real Madrid",
            team_id=87,
            match_id=999,
            elapsed_time=60,
            league_id=10
        )
        logs = NotificationLog.objects.filter(topic="match_999", event_type="SUBSTITUTION")
        self.assertTrue(logs.exists())
        log = logs.last()
        self.assertEqual(log.data.get("type"), "match")
        self.assertEqual(log.data.get("event_type"), "SUBSTITUTION")
        self.assertEqual(log.data.get("player_in"), "Mbappe")
        self.assertEqual(log.data.get("player_out"), "Vinicius")
        self.assertEqual(log.data.get("elapsed"), "60")

    def test_send_var_alert_data_payload(self):
        from .services import NotificationService
        NotificationService.send_var_alert(
            detail="Goal Disallowed",
            team_name="Real Madrid",
            team_id=87,
            match_id=999,
            elapsed_time=75,
            league_id=10
        )
        logs = NotificationLog.objects.filter(topic="match_999", event_type="VAR")
        self.assertTrue(logs.exists())
        log = logs.last()
        self.assertEqual(log.data.get("type"), "match")
        self.assertEqual(log.data.get("event_type"), "VAR")
        self.assertEqual(log.data.get("detail"), "Goal Disallowed")
        self.assertEqual(log.data.get("elapsed"), "75")

    def test_send_match_result_alert_data_payload(self):
        from .services import NotificationService
        from sports.models import Team
        home_team = Team.objects.create(id=850, name="Home FC")
        away_team = Team.objects.create(id=851, name="Away FC")
        NotificationService.send_match_result_alert(
            home_team=home_team,
            away_team=away_team,
            score="2 - 1",
            match_id=9991,
            league_id=10
        )
        logs = NotificationLog.objects.filter(topic="match_9991", event_type="FULL_TIME")
        self.assertTrue(logs.exists())
        log = logs.last()
        self.assertEqual(log.data.get("type"), "match")
        self.assertEqual(log.data.get("event_type"), "FULL_TIME")
        self.assertEqual(log.data.get("match_id"), "9991")

    def test_send_lineup_alert_data_payload(self):
        from .services import NotificationService
        from sports.models import Team
        home_team = Team.objects.create(id=860, name="Home FC")
        away_team = Team.objects.create(id=861, name="Away FC")
        NotificationService.send_lineup_alert(
            home_team=home_team,
            away_team=away_team,
            match_id=9992,
            league_id=10
        )
        logs = NotificationLog.objects.filter(topic="match_9992", event_type="LINEUPS")
        self.assertTrue(logs.exists())
        log = logs.last()
        self.assertEqual(log.data.get("type"), "match")
        self.assertEqual(log.data.get("event_type"), "LINEUPS")
        self.assertEqual(log.data.get("match_id"), "9992")

    def test_send_league_daily_update_data_payload(self):
        from .services import NotificationService
        NotificationService.send_league_daily_update(
            league_name="Premier League",
            match_count=5,
            league_id=39
        )
        logs = NotificationLog.objects.filter(topic="league_39", event_type="SCHEDULE")
        self.assertTrue(logs.exists())
        log = logs.last()
        self.assertEqual(log.data.get("type"), "league")
        self.assertEqual(log.data.get("event_type"), "SCHEDULE")
        self.assertEqual(log.data.get("league_id"), "39")



from django.utils import timezone
from datetime import timedelta

class UpcomingMatchesNotificationTests(TestCase):
    def setUp(self):
        from sports.models import Team, League, Fixture, Season
        self.home_team = Team.objects.create(id=9001, name="Home FC")
        self.away_team = Team.objects.create(id=9002, name="Away FC")
        self.league = League.objects.create(id=900, name="Super League", season_year=2026)
        self.season = Season.objects.create(year=2026)
        
        self.now = timezone.now()
        fixture_date = self.now + timedelta(minutes=15)
        # Create a fixture starting in 15 minutes
        self.fixture = Fixture.objects.create(
            id=99001,
            home_team=self.home_team,
            away_team=self.away_team,
            league=self.league,
            season=self.season,
            date=fixture_date,
            timestamp=int(fixture_date.timestamp()),
            status_short="NS"
        )
        
    def test_upcoming_match_notification_flow(self):
        from users.models import GuestFavorite
        from sports.tasks import check_upcoming_matches_and_notify
        
        # Setup guest user following the fixture
        guest_id = "test_guest_uuid"
        guest_fav = GuestFavorite.objects.create(device_id=guest_id)
        guest_fav.favorite_fixtures.add(self.fixture)
        
        # Register device with Spanish language
        device = UserDevice.objects.create(
            registration_id="guest_token_es",
            guest_id=guest_id,
            language="es",
            active=True
        )
        
        # Sync subscriptions (this internally subscribes device to topic)
        from .services import sync_device_subscriptions
        sync_device_subscriptions(device)
        
        # Run the celery task
        res = check_upcoming_matches_and_notify()
        self.assertEqual(res, "Sent pre-match alerts for 1 fixtures.")
        
        # Verify a base NotificationLog exists for match_99001
        base_log = NotificationLog.objects.filter(topic="match_99001", event_type="MATCH_START").first()
        self.assertIsNotNone(base_log)
        self.assertEqual(base_log.title, "⏳ Kickoff Soon")
        
        # Check that duplicate check prevents double notify
        res_second = check_upcoming_matches_and_notify()
        self.assertEqual(res_second, "Sent pre-match alerts for 0 fixtures.")

    def test_sync_device_subscriptions_guest_league(self):
        from users.models import GuestFavorite
        from .services import sync_device_subscriptions
        
        guest_id = "guest_league_test_uuid"
        guest_fav = GuestFavorite.objects.create(device_id=guest_id)
        guest_fav.favorite_leagues.add(self.league)
        
        device = UserDevice.objects.create(
            registration_id="guest_token_league",
            guest_id=guest_id,
            language="tr",
            active=True
        )
        
        # This should not raise any errors, and subscribe the device to league_900 topic
        sync_device_subscriptions(device)
