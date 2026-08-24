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
