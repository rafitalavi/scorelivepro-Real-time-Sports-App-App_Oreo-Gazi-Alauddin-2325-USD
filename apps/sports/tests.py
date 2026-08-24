from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Team, TeamSquad, PlayerProfile, Season, League, PlayerStatList, Venue, TeamStatistic, TeamCoachList, Fixture, FixtureLineup, FixtureStatistic

class TeamSquadTests(APITestCase):
    def setUp(self):
        self.team = Team.objects.create(
            id=33,
            name="Manchester United",
            logo="https://example.com/logo.png"
        )
        self.url = reverse('team-detail', kwargs={'pk': self.team.id})

    @patch('requests.get')
    def test_get_team_details_includes_squad_and_fetches_from_api(self, mock_get):
        # Mock API-Football response
        mock_response = {
            "response": [
                {
                    "team": {"id": 33, "name": "Manchester United"},
                    "players": [
                        {
                            "id": 882,
                            "name": "David de Gea",
                            "age": 31,
                            "number": 1,
                            "position": "Goalkeeper",
                            "photo": "https://example.com/photo.png"
                        }
                    ]
                }
            ]
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        # Request team details
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify response contains the squad players
        self.assertIn('squad', response.data)
        self.assertEqual(len(response.data['squad']), 1)
        self.assertEqual(response.data['squad'][0]['name'], "David de Gea")

        # Verify it was saved to the database
        squad = TeamSquad.objects.get(team=self.team)
        self.assertEqual(len(squad.players), 1)
        self.assertEqual(squad.players[0]['name'], "David de Gea")

        # Verify requests.get was called
        mock_get.assert_called_once()

        # Call again: it should use the database cache and NOT call requests.get again
        mock_get.reset_mock()
        response_cached = self.client.get(self.url)
        self.assertEqual(response_cached.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_cached.data['squad']), 1)
        mock_get.assert_not_called()


class PlayerProfileTests(APITestCase):
    def setUp(self):
        self.player_id = 22236
        self.season = 2026
        self.url = reverse('player-detail', kwargs={'pk': self.player_id})

    @patch('requests.get')
    def test_get_player_details_fetches_from_api_and_caches(self, mock_get):
        # Mock API-Football response
        mock_response = {
            "response": [
                {
                    "player": {
                        "id": 22236,
                        "name": "Rafael Leão",
                        "firstname": "Rafael",
                        "lastname": "Leão"
                    },
                    "statistics": [
                        {
                            "team": {"id": 489, "name": "AC Milan"},
                            "games": {"appearences": 25, "position": "Attacker"}
                        }
                    ]
                }
            ]
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        # Request player details
        response = self.client.get(f"{self.url}?season={self.season}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify response matches
        self.assertEqual(response.data['player_id'], self.player_id)
        self.assertEqual(response.data['season'], self.season)
        self.assertEqual(response.data['data']['player']['name'], "Rafael Leão")

        # Verify database save
        profile = PlayerProfile.objects.get(player_id=self.player_id, season=self.season)
        self.assertEqual(profile.data['player']['name'], "Rafael Leão")

        # Verify requests.get was called
        mock_get.assert_called_once()

        # Second request: should not hit the API
        mock_get.reset_mock()
        response_cached = self.client.get(f"{self.url}?season={self.season}")
        self.assertEqual(response_cached.status_code, status.HTTP_200_OK)
        self.assertEqual(response_cached.data['data']['player']['name'], "Rafael Leão")
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_player_details_defaults_to_latest_season_in_db(self, mock_get):
        # Create a newer season in database
        Season.objects.create(year=2028)
        
        # Mock API-Football response for season 2028
        mock_response = {
            "response": [
                {
                    "player": {
                        "id": 22236,
                        "name": "Rafael Leão"
                    },
                    "statistics": []
                }
            ]
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        # Request player details without season param
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify it default to the 2028 season
        self.assertEqual(response.data['season'], 2028)
        mock_get.assert_called_once()


class PlayerStatListsTests(APITestCase):
    def setUp(self):
        self.season_year = 2026
        self.season = Season.objects.create(year=self.season_year)
        self.league = League.objects.create(id=39, name="Premier League", season_year=self.season_year)

    def test_missing_league(self):
        for name in ['topscorers', 'topassists', 'topyellowcards', 'topredcards']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data['error'], "league parameter is required.")

    @patch('requests.get')
    def test_fetches_and_caches_all_types(self, mock_get):
        endpoints = [
            ('topscorers', "Harry Kane"),
            ('topassists', "Kevin De Bruyne"),
            ('topyellowcards', "Casemiro"),
            ('topredcards', "Granit Xhaka")
        ]
        
        for name, player_name in endpoints:
            mock_response = {
                "response": [
                    {
                        "player": {"id": 100, "name": player_name},
                        "statistics": []
                    }
                ]
            }
            mock_get.reset_mock()
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            url = reverse(name)
            response = self.client.get(f"{url}?league={self.league.id}&season={self.season_year}")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['league'], self.league.id)
            self.assertEqual(response.data['season'], self.season_year)
            self.assertEqual(response.data['stat_type'], name)
            self.assertEqual(response.data['data'][0]['player']['name'], player_name)

            # Verify database cache
            record = PlayerStatList.objects.get(league=self.league, season=self.season, stat_type=name)
            self.assertEqual(record.data[0]['player']['name'], player_name)


class TeamStatsVenuesCoachesTests(APITestCase):
    def setUp(self):
        self.season_year = 2026
        self.season = Season.objects.create(year=self.season_year)
        self.league = League.objects.create(id=39, name="Premier League", season_year=self.season_year)
        self.team = Team.objects.create(id=33, name="Manchester United")
        self.venue = Venue.objects.create(id=281, name="Old Trafford", city="Manchester")

    def test_team_statistics_missing_params(self):
        response = self.client.get(reverse('team-statistics'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "Both team and league parameters are required.")

    @patch('requests.get')
    def test_team_statistics_success(self, mock_get):
        mock_response = {
            "response": {
                "form": "WLLW",
                "fixtures": {"played": {"total": 4}}
            }
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        url = f"{reverse('team-statistics')}?team={self.team.id}&league={self.league.id}&season={self.season_year}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['form'], "WLLW")

        # Verify DB caching
        record = TeamStatistic.objects.get(team=self.team, league=self.league, season=self.season)
        self.assertEqual(record.data['form'], "WLLW")

    @patch('requests.get')
    def test_venue_details_fetch_and_cache(self, mock_get):
        mock_response = {
            "response": [
                {
                    "id": 281,
                    "name": "Old Trafford",
                    "city": "Manchester",
                    "address": "Sir Matt Busby Way",
                    "country": "England",
                    "capacity": 74140,
                    "surface": "grass",
                    "image": "https://example.com/ot.png"
                }
            ]
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        # Request specific venue details
        url = f"{reverse('venue-list')}?id={self.venue.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['capacity'], 74140)

        # Verify DB caching
        venue = Venue.objects.get(id=self.venue.id)
        self.assertEqual(venue.capacity, 74140)
        self.assertEqual(venue.address, "Sir Matt Busby Way")

    @patch('requests.get')
    def test_team_coaches_fetch_and_cache(self, mock_get):
        mock_response = {
            "response": [
                {
                    "id": 1993,
                    "name": "E. ten Hag",
                    "nationality": "Netherlands"
                }
            ]
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        # Request coaches
        url = f"{reverse('coachs-list')}?team={self.team.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data'][0]['name'], "E. ten Hag")

        # Verify DB caching
        record = TeamCoachList.objects.get(team=self.team)
        self.assertEqual(record.data[0]['name'], "E. ten Hag")


class FixtureOnDemandTests(APITestCase):
    def setUp(self):
        from django.utils import timezone
        self.season = Season.objects.create(year=2026)
        self.league = League.objects.create(id=39, name="Premier League", season_year=2026)
        self.home_team = Team.objects.create(id=33, name="Manchester United")
        self.away_team = Team.objects.create(id=34, name="Chelsea")
        self.fixture = Fixture.objects.create(
            id=1001,
            league=self.league,
            season=self.season,
            home_team=self.home_team,
            away_team=self.away_team,
            date=timezone.now(),
            timestamp=int(timezone.now().timestamp()),
            status_short='1H',  # Live match
            events=[]
        )
        self.detail_url = reverse('fixture-detail', kwargs={'pk': self.fixture.id})
        self.lineups_url = reverse('fixture-lineups', kwargs={'pk': self.fixture.id})
        self.stats_url = reverse('fixture-statistics', kwargs={'pk': self.fixture.id})

    @patch('requests.get')
    def test_fixture_detail_events_fetch_and_cooldown(self, mock_get):
        from datetime import timedelta
        from django.utils import timezone
        # Set updated_at to the past so cooldown doesn't block the first request
        Fixture.objects.filter(id=1001).update(updated_at=timezone.now() - timedelta(minutes=10))
        
        # 1. Mock API call returning some events
        mock_response = {
            "response": [
                {
                    "fixture": {"id": 1001, "status": {"short": "1H"}},
                    "events": [{"time": {"elapsed": 12}, "team": {"id": 33}, "player": {"name": "Rashford"}, "type": "Goal"}]
                }
            ]
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        # Request details (should fetch and populate events)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get.assert_called_once()

        # Verify DB is updated
        self.fixture.refresh_from_db()
        self.assertEqual(len(self.fixture.events), 1)

        # 2. Clear events in DB to force another check, but keep updated_at recent (cooldown active)
        self.fixture.events = []
        self.fixture.save()

        # Reset mock and request again: it should NOT trigger requests.get due to 5-minute cooldown
        mock_get.reset_mock()
        response_cooldown = self.client.get(self.detail_url)
        self.assertEqual(response_cooldown.status_code, status.HTTP_200_OK)
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_fixture_lineups_fetch_and_cooldown(self, mock_get):
        # 1. Mock API call returning empty list to simulate lineups not available yet
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"response": []}

        # Request lineups (should trigger API fetch because object is newly created)
        response = self.client.get(self.lineups_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get.assert_called_once()

        # 2. Reset mock and request again: should NOT hit API due to 5-minute cooldown
        mock_get.reset_mock()
        response_cooldown = self.client.get(self.lineups_url)
        self.assertEqual(response_cooldown.status_code, status.HTTP_200_OK)
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_fixture_statistics_fetch_and_cooldown(self, mock_get):
        # 1. Mock API call returning empty list
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"response": []}

        # Request stats (should trigger API fetch because object is newly created)
        response = self.client.get(self.stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get.assert_called_once()

        # 2. Reset mock and request again: should NOT hit API due to 5-minute cooldown
        mock_get.reset_mock()
        response_cooldown = self.client.get(self.stats_url)
        self.assertEqual(response_cooldown.status_code, status.HTTP_200_OK)
        mock_get.assert_not_called()
