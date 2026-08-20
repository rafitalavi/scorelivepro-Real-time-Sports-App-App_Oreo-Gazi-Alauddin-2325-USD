from rest_framework import serializers
from .models import (Season, Country, League, Team, Venue, Standing, 
                     Fixture, Timezone, FixtureLineup, FixtureStatistic, HeadToHead,
                     FavoriteTeam, FavoriteLeague, TeamSquad, PlayerProfile, PlayerStatList,
                     TeamStatistic, TeamCoachList)

class TimezoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timezone
        fields = ['name']

class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ['id', 'name', 'city', 'address', 'country', 'capacity', 'surface', 'image', 'updated_at']

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'logo', 'country', 'is_popular']

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['name', 'code', 'flag']

class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = ['year']

class LeagueSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)
    class Meta:
        model = League
        fields = ['id', 'name', 'country', 'logo', 'season_year']

class TeamDetailSerializer(serializers.ModelSerializer):
    venue = VenueSerializer(read_only=True)
    leagues = LeagueSerializer(many=True, read_only=True)
    squad = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['id', 'name', 'logo', 'code', 'country', 'venue', 'leagues', 'squad', 'updated_at']

    def get_squad(self, obj):
        try:
            return obj.squad.players
        except TeamSquad.DoesNotExist:
            return []


class StandingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Standing
        fields = ['league', 'season', 'data', 'updated_at']

# --- FIXTURE SERIALIZERS ---

class FixtureSerializer(serializers.ModelSerializer):
    """
    Lightweight Serializer for Lists & WebSocket.
    """
    league = LeagueSerializer(read_only=True)
    home_team = TeamSerializer(read_only=True)
    away_team = TeamSerializer(read_only=True)
    venue = VenueSerializer(read_only=True)
    season = SeasonSerializer(read_only=True)

    class Meta:
        model = Fixture
        fields = [
            'id', 'date', 'timestamp', 'timezone', 'referee', 'round',
            'status_long', 'status_short', 'elapsed',
            'venue', 'league', 'season', 'home_team', 'away_team',
            'goals', 'score', 'periods', 'events'
        ]

class FixtureLineupSerializer(serializers.ModelSerializer):
    class Meta:
        model = FixtureLineup
        fields = ['home', 'away', 'updated_at']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        def inject_photos(team_data):
            if not isinstance(team_data, dict):
                return
            # Process startXI
            start_xi = team_data.get('startXI', [])
            if isinstance(start_xi, list):
                for item in start_xi:
                    if isinstance(item, dict) and 'player' in item:
                        player = item['player']
                        if isinstance(player, dict) and 'id' in player:
                            player['photo'] = f"https://media.api-sports.io/football/players/{player['id']}.png"
            
            # Process substitutes
            substitutes = team_data.get('substitutes', [])
            if isinstance(substitutes, list):
                for item in substitutes:
                    if isinstance(item, dict) and 'player' in item:
                        player = item['player']
                        if isinstance(player, dict) and 'id' in player:
                            player['photo'] = f"https://media.api-sports.io/football/players/{player['id']}.png"

        inject_photos(representation.get('home'))
        inject_photos(representation.get('away'))
        return representation

class FixtureStatisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = FixtureStatistic
        fields = ['data', 'updated_at']

class HeadToHeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeadToHead
        fields = [
            'team_1', 'team_2', 
            'team_1_wins', 'team_2_wins', 'draws', 
            'total_played', 'history', 'updated_at'
        ]


class FavoriteIDSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="The ID of the Team or League you want to favorite.")


class FavoriteTeamSerializer(serializers.ModelSerializer):
    team_details = TeamSerializer(source='team', read_only=True)

    class Meta:
        model = FavoriteTeam
        fields = ['id', 'user', 'team_details', 'created_at']


class FavoriteLeagueSerializer(serializers.ModelSerializer):
    league_details = LeagueSerializer(source='league', read_only=True)

    class Meta:
        model = FavoriteLeague
        fields = ['id', 'user', 'league_details', 'created_at']


class PlayerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerProfile
        fields = ['player_id', 'season', 'data', 'updated_at']


class PlayerStatListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerStatList
        fields = ['league', 'season', 'stat_type', 'data', 'updated_at']


class TeamStatisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamStatistic
        fields = ['team', 'league', 'season', 'data', 'updated_at']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if isinstance(representation.get('data'), dict):
            form = representation['data'].get('form')
            if isinstance(form, str):
                representation['data']['form'] = form[-10:]
        return representation


class TeamCoachListSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamCoachList
        fields = ['team', 'data', 'updated_at']