from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import FanProfile, GuestFavorite
from sports.models import Team, League
from notifications.models import UserDevice

User = get_user_model()

class GuestFavoritesTests(APITestCase):
    def setUp(self):
        # Create test Team and League
        self.team = Team.objects.create(id=1, name="FC Test Team")
        self.league = League.objects.create(id=1, name="Test League", type="League", season_year=2026)
        
        # Create test User
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="User",
            is_active=True
        )
        # Create user profile (usually signal handles it, let's make sure it exists)
        self.profile, _ = FanProfile.objects.get_or_create(user=self.user)

    def test_anonymous_device_registration(self):
        url = reverse('register-device')
        data = {
            "registration_id": "test_fcm_token_guest",
            "type": "android",
            "guest_id": "guest_uuid_123"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(UserDevice.objects.filter(guest_id="guest_uuid_123").exists())

    def test_anonymous_device_registration_requires_guest_id(self):
        url = reverse('register-device')
        data = {
            "registration_id": "test_fcm_token_guest_no_id",
            "type": "android"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guest_favorites_crud(self):
        # 1. List favorites (should be empty)
        url_teams = reverse('manage-fav-teams')
        response = self.client.get(url_teams, HTTP_X_GUEST_ID="guest_uuid_123")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # 2. Add favorite team
        response = self.client.post(url_teams, {"id": self.team.id}, HTTP_X_GUEST_ID="guest_uuid_123", format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check in DB
        guest_fav = GuestFavorite.objects.get(device_id="guest_uuid_123")
        self.assertIn(self.team, guest_fav.favorite_teams.all())

        # 3. Retrieve favorites again
        response = self.client.get(url_teams, HTTP_X_GUEST_ID="guest_uuid_123")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.team.id)

        # 4. Remove favorite team
        response = self.client.delete(url_teams, {"id": self.team.id}, HTTP_X_GUEST_ID="guest_uuid_123", format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.team, guest_fav.favorite_teams.all())

    def test_bulk_sync_favorites(self):
        # 1. Create a guest device registration
        UserDevice.objects.create(
            guest_id="guest_uuid_sync",
            registration_id="fcm_token_to_sync",
            type="android",
            active=True
        )

        # 2. Create guest favorites
        guest_fav = GuestFavorite.objects.create(device_id="guest_uuid_sync")
        guest_fav.favorite_teams.add(self.team)
        guest_fav.favorite_leagues.add(self.league)

        # Authenticate User
        self.client.force_authenticate(user=self.user)

        # 3. Call sync endpoint
        url = reverse('favorites-bulk-sync')
        response = self.client.post(url, {"guest_id": "guest_uuid_sync"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 4. Verify DB changes
        # User fan profile should have the favorites now
        self.assertIn(self.team, self.profile.favorite_teams.all())
        self.assertIn(self.league, self.profile.favorite_leagues.all())

        # GuestFavorite object should be deleted
        self.assertFalse(GuestFavorite.objects.filter(device_id="guest_uuid_sync").exists())

        # Device token should belong to the authenticated user now
        device = UserDevice.objects.get(registration_id="fcm_token_to_sync")
        self.assertEqual(device.user, self.user)
        self.assertIsNone(device.guest_id)
