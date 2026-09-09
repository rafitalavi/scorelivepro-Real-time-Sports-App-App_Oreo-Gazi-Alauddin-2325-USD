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

_COUNTRY_CACHE = {}

def get_cached_country(country_name):
    if not country_name:
        return None
    key = country_name.lower().strip()
    if key in _COUNTRY_CACHE:
        return _COUNTRY_CACHE[key]
    country_obj = Country.objects.filter(name__iexact=country_name).first()
    _COUNTRY_CACHE[key] = country_obj
    return country_obj

class TeamSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['id', 'name', 'logo', 'country', 'is_popular']

    def get_logo(self, obj):
        if not obj.logo:
            return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHgAAAB4CAYAAAA5ZDbSAAADj0lEQVR4nO2dO44UQRBEA8QVMBBXwELCw8ThxDiY6yFhcYXVGnuIxWqpp9TzqarMysjseP6MsuN1VFWPNDOAEEIIIYQQQgghhBAZeBc9gAfPL69vo6/9/OljqUzSX8yMzEfJLD3l4CukXiOb7DTDRkq9RgbZ9AMyim1hFk07WAaxLYyi6QbKKLaFSTTNIBXEtjCIfh89AFBTLsBxXaF3GEMAq4hqc1iDzyQXiLveEMFnk7sRcd1Ll42zij1i1ZK9rMGSe8mqPJYIltxjVuTiLlhyb+Odj6tgyX0Mz5zcBEtuH155UXySJfxwEaz2juGRm/mz2MyQv34/WY4Sys8f34dfa/mMbNpgNdcGyxy1Bxfng9UbWbf329cvlm+3hD9//5m91/PL65vFUm3SYC3NPljkqiW6ONOC1V5fZvNVg4szJVjtXcNMzmpwcYYFq71rGc1bDS7OkGC1N4aR3NXg4khwcboFa3mOpTd/Nbg4ElycLsFanjno8aAGF0eCiyPBxZHg4jwsWAcsLh71oQYXR4KLI8HFkeDiSHBxJLg4tIItvwayAtZ5qQS3X7lkDa2lnXPmq6PWUAkGuMIZgW1+OsHAZUjsLd7PxyYXIBXcwiqZda49tILZ92PmfXcPrWCAV3IWuQC5YIBPcia5QIfgyJ+nZw0xcq5HfdA3eIPhZM1+Yj4ijeCW1ZKjt4ZRUgmO2o+z7bt7UgkG1kvOLBfoFMzwP0DAOsmscns8pGvwxuqwWeT2klYw4HuyznhiPqJbMMsyfYSVZOYTc2/+qRsM2O/HrPvuKOkFA3aSq8kFBgUzLtOzkjPIHcm9RIM3rKQwyh1lWDBji4Gxk3WGE/No3qUafMQ9ycwnZgumBGdoMXBdYoZ9F5jLuWyD70nOIneWacGsLQauS84kdzbfsg3euCePWa4FZu1j/wWAoz/dYpdL868rAPdSnRGrPMsv0RttW9nba4WpYPYWb1LZ5Vrm6CKEfT9mxrokLks0e5NZ8cjtNHvwWXETrBb34ZWXa4Ml+TE8c3JfoiX5Nt75LNmDJfmYFbksO2RJ8iWr8ggJ/czPyatv9JDHpLO2OeK6w56DzyY56nopQq68ZEffyBSfZEWH4AXDdYUP0FKhzQxiN2gGackomknsBt1ALRlEM4rdoB2shVE0s9gN+gGPiJSdQeqeVMMesUJ2Nql70g5+ixnpmWUKIYQQQgghhBBClOY/KLaJ6Lco0JYAAAAASUVORK5CYII="
        return obj.logo

    def get_country(self, obj):
        if not obj.country:
            return None
        
        # Prevent N+1 queries by reading countries map from context if available, otherwise in-process cache
        countries_map = self.context.get('countries_map') if self.context else None
        if countries_map is not None:
            country_obj = countries_map.get(obj.country.lower())
        else:
            country_obj = get_cached_country(obj.country)
            
        if country_obj:
            return CountrySerializer(country_obj).data
            
        return {
            "name": obj.country,
            "code": "",
            "flag": ""
        }

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['name', 'code', 'flag']

class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = ['year']

REGION_LOCALIZATIONS = {
    "Europe": {
        "en": "Europe", "it": "Europa", "es": "Europa", "fr": "Europe",
        "de": "Europa", "pt": "Europa", "tr": "Avrupa"
    },
    "Africa": {
        "en": "Africa", "it": "Africa", "es": "África", "fr": "Afrique",
        "de": "Afrika", "pt": "África", "tr": "Afrika"
    },
    "Asia": {
        "en": "Asia", "it": "Asia", "es": "Asia", "fr": "Asie",
        "de": "Asien", "pt": "Ásia", "tr": "Asya"
    },
    "South America": {
        "en": "South America", "it": "Sud America", "es": "Sudamérica", "fr": "Amérique du Sud",
        "de": "Südamerika", "pt": "América do Sul", "tr": "Güney Amerika"
    },
    "North & Central America": {
        "en": "North & Central America", "it": "Nord e Centro America", "es": "Norte y Centroamérica",
        "fr": "Amérique du Nord et Centrale", "de": "Nord- und Mittelamerika", "pt": "América do Norte e Central", "tr": "Kuzey ve Orta Amerika"
    },
    "Oceania": {
        "en": "Oceania", "it": "Oceania", "es": "Oceanía", "fr": "Océanie",
        "de": "Ozeanien", "pt": "Oceania", "tr": "Okyanusya"
    },
    "World": {
        "en": "World", "it": "Mondo", "es": "Mundo", "fr": "Monde",
        "de": "Welt", "pt": "Mundo", "tr": "Dünya"
    }
}

class LeagueSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)
    name = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    localized_region = serializers.SerializerMethodField()

    class Meta:
        model = League
        fields = ['id', 'name', 'country', 'region', 'localized_region', 'logo', 'season_year']

    def get_region(self, obj):
        return obj.region or "World"

    def get_localized_region(self, obj):
        reg = obj.region or "World"
        return REGION_LOCALIZATIONS.get(reg, REGION_LOCALIZATIONS["World"])

    def get_name(self, obj):
        generic_names = {
            "Super League", "Premier League", "League One", "League Two", 
            "FA Cup", "Cup", "Super Cup", "Championship", "Division 1", 
            "Division 2", "Pro League", "National League", "Primeira Liga",
            "Superliga", "Primera Division", "Primera División", "Second Division",
            "Serie A", "Série A", "Serie B", "Série B", "Play-offs 1/2", "Play-offs 2/3"
        }
        if obj.name in generic_names and obj.country and obj.country.name not in ("World", "International"):
            return f"{obj.name} ({obj.country.name})"
        return obj.name

class TeamDetailSerializer(serializers.ModelSerializer):
    venue = VenueSerializer(read_only=True)
    leagues = LeagueSerializer(many=True, read_only=True)
    squad = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    flag = serializers.SerializerMethodField()
    founded = serializers.SerializerMethodField()
    national = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['id', 'name', 'logo', 'code', 'country', 'venue', 'leagues', 'squad', 'flag', 'founded', 'national', 'updated_at']

    def get_logo(self, obj):
        if not obj.logo:
            return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHgAAAB4CAYAAAA5ZDbSAAADj0lEQVR4nO2dO44UQRBEA8QVMBBXwELCw8ThxDiY6yFhcYXVGnuIxWqpp9TzqarMysjseP6MsuN1VFWPNDOAEEIIIYQQQgghhBAZeBc9gAfPL69vo6/9/OljqUzSX8yMzEfJLD3l4CukXiOb7DTDRkq9RgbZ9AMyim1hFk07WAaxLYyi6QbKKLaFSTTNIBXEtjCIfh89AFBTLsBxXaF3GEMAq4hqc1iDzyQXiLveEMFnk7sRcd1Ll42zij1i1ZK9rMGSe8mqPJYIltxjVuTiLlhyb+Odj6tgyX0Mz5zcBEtuH155UXySJfxwEaz2juGRm/mz2MyQv34/WY4Sys8f34dfa/mMbNpgNdcGyxy1Bxfng9UbWbf329cvlm+3hD9//5m91/PL65vFUm3SYC3NPljkqiW6ONOC1V5fZvNVg4szJVjtXcNMzmpwcYYFq71rGc1bDS7OkGC1N4aR3NXg4khwcboFa3mOpTd/Nbg4ElycLsFanjno8aAGF0eCiyPBxZHg4jwsWAcsLh71oQYXR4KLI8HFkeDiSHBxJLg4tIItvwayAtZ5qQS3X7lkDa2lnXPmq6PWUAkGuMIZgW1+OsHAZUjsLd7PxyYXIBXcwiqZda49tILZ92PmfXcPrWCAV3IWuQC5YIBPcia5QIfgyJ+nZw0xcq5HfdA3eIPhZM1+Yj4ijeCW1ZKjt4ZRUgmO2o+z7bt7UgkG1kvOLBfoFMzwP0DAOsmscns8pGvwxuqwWeT2klYw4HuyznhiPqJbMMsyfYSVZOYTc2/+qRsM2O/HrPvuKOkFA3aSq8kFBgUzLtOzkjPIHcm9RIM3rKQwyh1lWDBji4Gxk3WGE/No3qUafMQ9ycwnZgumBGdoMXBdYoZ9F5jLuWyD70nOIneWacGsLQauS84kdzbfsg3euCePWa4FZu1j/wWAoz/dYpdL868rAPdSnRGrPMsv0RttW9nba4WpYPYWb1LZ5Vrm6CKEfT9mxrokLks0e5NZ8cjtNHvwWXETrBb34ZWXa4Ml+TE8c3JfoiX5Nt75LNmDJfmYFbksO2RJ8iWr8ggJ/czPyatv9JDHpLO2OeK6w56DzyY56nopQq68ZEffyBSfZEWH4AXDdYUP0FKhzQxiN2gGackomknsBt1ALRlEM4rdoB2shVE0s9gN+gGPiJSdQeqeVMMesUJ2Nql70g5+ixnpmWUKIYQQQgghhBBClOY/KLaJ6Lco0JYAAAAASUVORK5CYII="
        return obj.logo

    def get_squad(self, obj):
        try:
            return obj.squad.players
        except TeamSquad.DoesNotExist:
            return []

    def get_flag(self, obj):
        if obj.country:
            country_obj = get_cached_country(obj.country)
            if country_obj:
                return country_obj.flag
        return ""

    def get_founded(self, obj):
        return None

    def get_national(self, obj):
        return False


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
    coverage = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Fixture
        fields = [
            'id', 'date', 'timestamp', 'timezone', 'referee', 'round',
            'status_long', 'status_short', 'elapsed', 'extra', 'status',
            'venue', 'league', 'season', 'home_team', 'away_team',
            'goals', 'score', 'periods', 'events', 'coverage'
        ]

    def get_coverage(self, obj):
        has_lineups = bool(hasattr(obj, 'lineup') and (obj.lineup.home or obj.lineup.away))
        has_stats = bool(hasattr(obj, 'statistic') and obj.statistic.data)
        has_events = bool(obj.events)
        return {
            "lineups": has_lineups,
            "statistics": has_stats,
            "events": has_events
        }

    def get_status(self, obj):
        return {
            "short": obj.status_short,
            "long": obj.status_long,
            "elapsed": obj.elapsed,
            "extra": obj.extra
        }

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

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        data_dict = representation.pop('data', {}) or {}
        if isinstance(data_dict, dict):
            representation['player'] = data_dict.get('player', {})
            representation['statistics'] = data_dict.get('statistics', [])
        else:
            representation['player'] = {}
            representation['statistics'] = []
        return representation


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