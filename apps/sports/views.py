import textwrap
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.shortcuts import get_object_or_404
from rest_framework import generics, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny

# Swagger / Documentation Imports
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse, extend_schema_view
from drf_spectacular.types import OpenApiTypes

from users.permissions import IsOwnerOrAdmin
from users.utils import log_activity
from .tasks import fetch_and_update_h2h_record
from .models import (HeadToHead, Timezone, Season, Country, League, Team, Venue, Standing, 
                     Fixture, FixtureLineup, FixtureStatistic, FavoriteTeam, FavoriteLeague, TeamSquad, PlayerProfile, PlayerStatList,
                     TeamStatistic, TeamCoachList)
from .serializers import (HeadToHeadSerializer, TimezoneSerializer, SeasonSerializer, CountrySerializer, 
                          LeagueSerializer, TeamSerializer, TeamDetailSerializer, VenueSerializer, 
                          StandingSerializer, FixtureSerializer, 
                          FixtureLineupSerializer, FixtureStatisticSerializer,
                          FavoriteTeamSerializer, FavoriteLeagueSerializer, FavoriteIDSerializer,
                          PlayerProfileSerializer, PlayerStatListSerializer,
                          TeamStatisticSerializer, TeamCoachListSerializer)

User = get_user_model()

# =========================================================
#                    PAGINATION CONFIG
# =========================================================

class StandardPagination(PageNumberPagination):
    """
    Standard pagination for returning 100 items per page.
    """
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000

# =========================================================
#                    ACTIVITY TRACKING MIXIN
# =========================================================

class ActivityLogMixin:
    """
    Mixin to automatically log when an authenticated user views a specific resource.
    """
    activity_action = "VIEW_RESOURCE"
    
    def get_activity_details(self, request, *args, **kwargs):
        return f"Viewed resource ID: {kwargs.get('pk') or kwargs.get('league_id')}"

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        if request.user and request.user.is_authenticated:
            details = self.get_activity_details(request, *args, **kwargs)
            # Fire and forget logging
            log_activity(request.user, self.activity_action, details, request=request)
        return response


# =========================================================
#                    WEBSOCKET DOCS
# =========================================================

@extend_schema(
    tags=['Fixtures'],
    summary="🔴 WebSocket: Live Score Stream",
    description=textwrap.dedent("""
        **Connect via:** `wss://<base_url>/ws/live/`
        
        Establishes a real-time WebSocket connection for live match updates.
        
        **Protocol Flow:**
        1. **Connect:** Client establishes connection.
        2. **Initial State:** Server immediately sends the full list of currently live matches.
        3. **Updates:** Server pushes updates (JSON) whenever scores, time, or status change.
    """),
    request=None,
    responses={
        101: OpenApiResponse(description="Switching Protocols (Connection Accepted)"),
        426: OpenApiResponse(description="Upgrade Required (Use a WebSocket Client)")
    }
)
class FixtureWebSocketDocsView(APIView):
    permission_classes = [IsOwnerOrAdmin] 

    def get(self, request, *args, **kwargs):
        return Response(
            {"detail": "Please connect via WebSocket (ws://...)"}, 
            status=status.HTTP_426_UPGRADE_REQUIRED
        )


# =========================================================
#                    CORE RESOURCES
# =========================================================

@extend_schema(tags=['Core Resources'], summary="List Timezones")
class TimezoneListView(generics.ListAPIView):
    queryset = Timezone.objects.all()
    serializer_class = TimezoneSerializer
    @method_decorator(cache_page(60 * 60 * 24 * 7))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

@extend_schema(tags=['Core Resources'], summary="List Countries")
class CountryListView(generics.ListAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    search_fields = ['name', 'code']
    @method_decorator(cache_page(60 * 60 * 24))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

@extend_schema(tags=['Core Resources'], summary="List Available Seasons")
class SeasonListView(generics.ListAPIView):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer
    ordering = ['-year']
    @method_decorator(cache_page(60 * 60 * 24))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

@extend_schema(
    tags=['Core Resources'],
    summary="List or Get Venue Details",
    parameters=[
        OpenApiParameter(name='id', description='Venue ID to get details for', required=False, type=int)
    ]
)
class VenueListView(generics.ListAPIView):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    search_fields = ['name', 'city']

    def dispatch(self, request, *args, **kwargs):
        if 'id' in request.GET:
            # Skip cache_page for single venue requests to handle DB-based TTL checking dynamically
            return super().dispatch(request, *args, **kwargs)
        return cache_page(60 * 60 * 24)(super().dispatch)(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        venue_id = request.query_params.get('id')
        if venue_id:
            try:
                venue_id = int(venue_id)
            except ValueError:
                return Response(
                    {"error": "Invalid id parameter. Must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from datetime import timedelta
            from django.utils import timezone
            need_fetch = False
            try:
                venue = Venue.objects.get(id=venue_id)
                # If fields like address or country are null, it might be a placeholder, so update/fetch the full info!
                if not venue.address or venue.updated_at < timezone.now() - timedelta(days=1):
                    need_fetch = True
            except Venue.DoesNotExist:
                need_fetch = True
                venue = None

            if need_fetch:
                from .tasks import fetch_and_update_venue_details
                data = fetch_and_update_venue_details(venue_id)
                if data is None and venue is None:
                    return Response(
                        {"error": "Venue details not found or failed to retrieve."},
                        status=status.HTTP_404_NOT_FOUND
                    )
                try:
                    venue = Venue.objects.get(id=venue_id)
                except Venue.DoesNotExist:
                    return Response(
                        {"error": "Venue details not found or failed to retrieve."},
                        status=status.HTTP_404_NOT_FOUND
                    )

            serializer = self.get_serializer(venue)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return super().list(request, *args, **kwargs)


# =========================================================
#                    LEAGUES & TEAMS
# =========================================================

@extend_schema(tags=['Leagues'], summary="List Leagues", description="Searchable list of leagues.")
class LeagueListView(generics.ListAPIView):
    queryset = League.objects.select_related('country').all()
    serializer_class = LeagueSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['country__name', 'type', 'has_standings']
    search_fields = ['name', 'country__name']
    
    @method_decorator(cache_page(60 * 60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

@extend_schema(tags=['Leagues'], summary="Get League Details")
class LeagueDetailView(generics.RetrieveAPIView):
    queryset = League.objects.select_related('country').all()
    serializer_class = LeagueSerializer
    @method_decorator(cache_page(60 * 60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

import django_filters

class TeamFilter(django_filters.FilterSet):
    country = django_filters.CharFilter(field_name='country', lookup_expr='iexact')

    class Meta:
        model = Team
        fields = ['country', 'leagues', 'is_popular']

@extend_schema(
    tags=['Teams'], 
    summary="List Teams", 
    description="Search teams or filter by country and league. Example: `?leagues=39` (Premier League)",
    parameters=[
        OpenApiParameter(name='leagues', description='Filter by League ID', required=False, type=int),
    ]
)
class TeamListView(generics.ListAPIView):
    serializer_class = TeamSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TeamFilter
    search_fields = ['name', 'country'] 
    ordering_fields = ['name', 'country']
    ordering = ['name']
    
    def get_queryset(self):
        return Team.objects.all()

    @method_decorator(cache_page(60 * 60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

@extend_schema(
    tags=['Teams'],
    summary="List Teams Grouped by Country",
    description="Returns all teams in the system grouped by country."
)
class TeamCountryGroupedView(APIView):
    @method_decorator(cache_page(60 * 60 * 24))
    def get(self, request, *args, **kwargs):
        from collections import defaultdict
        
        country_map = {c.name.lower(): c.flag for c in Country.objects.exclude(flag__isnull=True)}
        teams = Team.objects.all().only('id', 'name', 'logo', 'country').order_by('country', 'name')
        
        grouped = defaultdict(list)
        for team in teams:
            country_name = team.country or "International"
            grouped[country_name].append({
                "id": team.id,
                "name": team.name,
                "logo": team.logo
            })
            
        response_data = []
        for country_name in sorted(grouped.keys()):
            response_data.append({
                "country": country_name,
                "flag": country_map.get(country_name.lower()),
                "teams": grouped[country_name]
            })
            
        return Response(response_data, status=status.HTTP_200_OK)

@extend_schema(tags=['Teams'], summary="Get Team Details")
class TeamDetailView(generics.RetrieveAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamDetailSerializer
    @method_decorator(cache_page(60 * 60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

    def get_object(self):
        obj = super().get_object()
        from django.utils import timezone
        from datetime import timedelta
        
        need_fetch = False
        try:
            squad = obj.squad
            if squad.updated_at < timezone.now() - timedelta(hours=24):
                need_fetch = True
        except TeamSquad.DoesNotExist:
            need_fetch = True
            
        if need_fetch:
            from .tasks import fetch_and_update_team_squad
            fetch_and_update_team_squad(obj.id)
            obj.refresh_from_db()
            
        return obj


# =========================================================
#                    STANDINGS
# =========================================================

@extend_schema(tags=['Standings'], summary="List Standings")
class StandingListView(generics.ListAPIView):
    serializer_class = StandingSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['league', 'season']
    search_fields = ['league__name', 'league__country__name']
    ordering_fields = ['season', 'league__name']
    ordering = ['-season', 'league__name'] 

    def get_queryset(self): 
        return Standing.objects.select_related('league', 'season').all()

    @method_decorator(cache_page(60 * 60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

@extend_schema(tags=['Standings'], summary="Get Standing Details")
class StandingDetailView(generics.RetrieveAPIView):
    serializer_class = StandingSerializer
    def get_object(self):
        return get_object_or_404(
            Standing.objects.select_related('league', 'season'),
            league_id=self.kwargs.get('league_id'),
            season_id=self.kwargs.get('season_year')
        )
    @method_decorator(cache_page(60 * 60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)


# =========================================================
#                    FIXTURES
# =========================================================
from django.utils import timezone
from datetime import timedelta
@extend_schema(
    tags=['Fixtures'], 
    summary="List Fixtures",
    description="Retrieve fixtures filtered by status and league. Pagination enabled (100 per page).",
    parameters=[
        OpenApiParameter(
            name='status', 
            description='Filter by match status group: "live", "finished", "upcoming"', 
            required=False, 
            type=str,
            enum=['live', 'finished', 'upcoming']
        ),
    ]
)
class FixtureListView(generics.ListAPIView):
    serializer_class = FixtureSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
 
    filterset_fields = ['league', 'season']
    search_fields = ['home_team__name', 'away_team__name', 'league__name']
 
    LIVE_STATUSES      = Fixture.LIVE_STATUSES
    FINISHED_STATUSES  = Fixture.FINISHED_STATUSES
    UPCOMING_STATUSES  = Fixture.UPCOMING_STATUSES
 
    def get_queryset(self):
        queryset = Fixture.objects.select_related(
            'league', 'league__country', 'season', 'home_team', 'away_team', 'venue'
        ).all()

        team_param = self.request.query_params.get('team')
        year_param = self.request.query_params.get('year')

        if team_param:
            target_year = year_param or 2026
            from django.db.models import Q
            local_exists = Fixture.objects.filter(
                Q(home_team_id=team_param) | Q(away_team_id=team_param),
                season_id=target_year
            ).exists()
            if not local_exists:
                from .tasks import fetch_and_update_team_fixtures
                fetch_and_update_team_fixtures(team_param, target_year)

            from django.db.models import Q
            queryset = queryset.filter(Q(home_team_id=team_param) | Q(away_team_id=team_param))

        if year_param:
            queryset = queryset.filter(season_id=year_param)

        status_param = self.request.query_params.get('status')
        live_param   = self.request.query_params.get('live')
 
        if status_param == 'live' or live_param == 'true':
            queryset = queryset.filter(
                status_short__in=self.LIVE_STATUSES
            ).order_by('date')
 
        elif status_param == 'finished':
            queryset = queryset.filter(
                status_short__in=self.FINISHED_STATUSES
            ).order_by('-date')
 
        elif status_param == 'upcoming':
            now = timezone.now()
            queryset = queryset.filter(
                status_short__in=self.UPCOMING_STATUSES,
                date__gte=now - timedelta(hours=2),
            ).order_by('date')
 
        else:
            queryset = queryset.order_by('date')
 
        return queryset

@extend_schema(tags=['Fixtures'], summary="Get Fixture Details")
class FixtureDetailView(ActivityLogMixin, generics.RetrieveAPIView):
    queryset = Fixture.objects.select_related(
        'league', 'league__country', 'season', 'home_team', 'away_team', 'venue'
    ).all()
    serializer_class = FixtureSerializer
    activity_action = "VIEW_FIXTURE_DETAILS"
    def get_activity_details(self, request, *args, **kwargs):
        return f"Viewed match overview for Fixture {kwargs.get('pk')}"

@extend_schema(tags=['Fixture Details'], summary="Get Lineups")
class FixtureLineupsView(ActivityLogMixin, generics.RetrieveAPIView):
    serializer_class = FixtureLineupSerializer
    activity_action = "VIEW_FIXTURE_LINEUPS"
    def get_activity_details(self, request, *args, **kwargs):
        return f"Viewed lineups for Fixture {kwargs.get('pk')}"
    
    @method_decorator(cache_page(60 * 10))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

    def get_object(self):
        obj, _ = FixtureLineup.objects.get_or_create(fixture_id=self.kwargs['pk'])
        return obj

@extend_schema(tags=['Fixture Details'], summary="Get Statistics")
class FixtureStatisticsView(ActivityLogMixin, generics.RetrieveAPIView):
    serializer_class = FixtureStatisticSerializer
    activity_action = "VIEW_FIXTURE_STATS"
    def get_activity_details(self, request, *args, **kwargs):
        return f"Viewed statistics for Fixture {kwargs.get('pk')}"

    @method_decorator(cache_page(60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

    def get_object(self):
        obj, _ = FixtureStatistic.objects.get_or_create(fixture_id=self.kwargs['pk'])
        return obj

@extend_schema(tags=['Fixture Details'], summary="Get Head-to-Head")
class FixtureHeadToHeadView(ActivityLogMixin, generics.RetrieveAPIView):
    serializer_class = HeadToHeadSerializer
    activity_action = "VIEW_FIXTURE_H2H"
    def get_activity_details(self, request, *args, **kwargs):
        return f"Viewed Head-to-Head stats for Fixture {kwargs.get('pk')}"

    @method_decorator(cache_page(60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)
    
    def get_object(self):
        fixture_id = self.kwargs['pk']
        fixture = get_object_or_404(Fixture, id=fixture_id)
        t1 = fixture.home_team
        t2 = fixture.away_team
        
        if t1.id < t2.id:
            team_1, team_2 = t1, t2
        else:
            team_1, team_2 = t2, t1

        try:
            return HeadToHead.objects.get(team_1=team_1, team_2=team_2)
        except HeadToHead.DoesNotExist:
            print(f"H2H missing for {team_1.name} vs {team_2.name}. Fetching now...")
            fetch_and_update_h2h_record(team_1, team_2)
            return get_object_or_404(HeadToHead, team_1=team_1, team_2=team_2)


# =========================================================
#                    USER FAVORITES
# =========================================================

@extend_schema_view(
    get=extend_schema(
        tags=['User Favorites'],
        summary="List User Favorites",
        description="Get a list of favorite 'teams' or 'leagues' for a specific user.",
        parameters=[
            OpenApiParameter(
                name='type', 
                location=OpenApiParameter.PATH, 
                description="Type of favorite to retrieve ('teams' or 'leagues')", 
                required=True, 
                type=str, 
                enum=['teams', 'leagues']
            )
        ],
        responses={
            200: OpenApiResponse(
                description="List of favorites (Format depends on 'type' parameter)",
                examples=[
                    OpenApiExample("Teams Example", value=[{"id": 1, "team_details": {"name": "Arsenal"}}]),
                    OpenApiExample("Leagues Example", value=[{"id": 1, "league_details": {"name": "Premier League"}}])
                ]
            )
        }
    ),
    post=extend_schema(
        tags=['User Favorites'],
        summary="Add to Favorites",
        description="Add a specific Team ID or League ID to the user's favorites.",
        request=FavoriteIDSerializer,
        parameters=[
            OpenApiParameter(
                name='type', 
                location=OpenApiParameter.PATH, 
                enum=['teams', 'leagues']
            )
        ],
        responses={
            201: OpenApiResponse(description="Successfully added"),
            400: OpenApiResponse(description="Invalid ID or Type")
        }
    ),
    delete=extend_schema(
        tags=['User Favorites'],
        summary="Remove from Favorites",
        description="Delete a favorite item by the Item ID (Team ID or League ID), NOT the favorite record ID.",
        parameters=[
            OpenApiParameter(name='type', location=OpenApiParameter.PATH, enum=['teams', 'leagues']),
            OpenApiParameter(name='item_id', location=OpenApiParameter.PATH, type=int, description="The ID of the Team or League to remove")
        ],
        responses={
            204: OpenApiResponse(description="Successfully deleted"),
            404: OpenApiResponse(description="Favorite not found")
        }
    )
)
class ManageUserFavoritesView(APIView):
    permission_classes = [IsOwnerOrAdmin]

    def _get_type_config(self, type_name):
        if type_name == 'teams':
            return {
                'model': FavoriteTeam,
                'target_model': Team,
                'serializer': FavoriteTeamSerializer,
                'field': 'team' 
            }
        elif type_name == 'leagues':
            return {
                'model': FavoriteLeague,
                'target_model': League,
                'serializer': FavoriteLeagueSerializer,
                'field': 'league'
            }
        return None

    def get(self, request, user_id, type):
        config = self._get_type_config(type)
        if not config:
            return Response({"error": "Invalid type. Use 'teams' or 'leagues'."}, status=400)

        target_user = get_object_or_404(User, pk=user_id)
        queryset = config['model'].objects.filter(user=target_user)
        serializer = config['serializer'](queryset, many=True)
        return Response(serializer.data)

    def post(self, request, user_id, type):
        config = self._get_type_config(type)
        if not config:
            return Response({"error": "Invalid type"}, status=400)
        
        target_user = get_object_or_404(User, pk=user_id)

        serializer = FavoriteIDSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        obj_id = serializer.validated_data['id']
        target_obj = get_object_or_404(config['target_model'], pk=obj_id)

        create_kwargs = {'user': target_user, config['field']: target_obj}
        obj, created = config['model'].objects.get_or_create(**create_kwargs)

        if created:
            # Log this action to the request user
            log_activity(request.user, "ADD_FAVORITE", f"Added {type[:-1].capitalize()} ID {obj_id} to favorites", request)
            return Response({"status": "Added", "id": obj_id}, status=status.HTTP_201_CREATED)
        return Response({"status": "Already exists", "id": obj_id}, status=status.HTTP_200_OK)

    def delete(self, request, user_id, type, item_id):
        config = self._get_type_config(type)
        if not config:
            return Response({"error": "Invalid type"}, status=400)
        
        target_user = get_object_or_404(User, pk=user_id)

        filter_kwargs = {'user': target_user, f"{config['field']}_id": item_id}
        deleted_count, _ = config['model'].objects.filter(**filter_kwargs).delete()

        if deleted_count > 0:
            # Log this action to the request user
            log_activity(request.user, "REMOVE_FAVORITE", f"Removed {type[:-1].capitalize()} ID {item_id} from favorites", request)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    tags=['Players'],
    summary="Get Player Details",
    parameters=[
        OpenApiParameter(
            name='season',
            description='Season year (e.g. 2026)',
            required=False,
            type=int
        )
    ]
)
class PlayerDetailView(APIView):
    def get(self, request, pk):
        from django.utils import timezone
        from datetime import timedelta
        
        # Default to current active season/year
        season = request.query_params.get('season')
        if not season:
            current_year = timezone.now().year
            latest_season = Season.objects.filter(year__lte=current_year).order_by('-year').first()
            if not latest_season:
                latest_season = Season.objects.order_by('-year').first()
            season = latest_season.year if latest_season else current_year
        else:
            try:
                season = int(season)
            except ValueError:
                return Response(
                    {"error": "Invalid season parameter. Must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        player_id = pk
        need_fetch = False
        try:
            profile = PlayerProfile.objects.get(player_id=player_id, season=season)
            if profile.updated_at < timezone.now() - timedelta(hours=24):
                need_fetch = True
        except PlayerProfile.DoesNotExist:
            need_fetch = True
            profile = None

        if need_fetch:
            from .tasks import fetch_and_update_player_profile
            data = fetch_and_update_player_profile(player_id, season)
            if data:
                profile = PlayerProfile.objects.get(player_id=player_id, season=season)
            elif not profile:
                return Response(
                    {"error": "Player details not found or failed to retrieve from external provider."},
                    status=status.HTTP_404_NOT_FOUND
                )

        serializer = PlayerProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BasePlayerStatListView(APIView):
    stat_type = None  # To be overridden by subclasses

    def get(self, request):
        from django.utils import timezone
        from datetime import timedelta

        if not self.stat_type:
            return Response(
                {"error": "Developer configuration error: stat_type is not defined."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        league_id = request.query_params.get('league')
        if not league_id:
            return Response(
                {"error": "league parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            league_id = int(league_id)
        except ValueError:
            return Response(
                {"error": "Invalid league parameter. Must be an integer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        season_param = request.query_params.get('season')
        if not season_param:
            current_year = timezone.now().year
            latest_season = Season.objects.filter(year__lte=current_year).order_by('-year').first()
            if not latest_season:
                latest_season = Season.objects.order_by('-year').first()
            season_year = latest_season.year if latest_season else current_year
        else:
            try:
                season_year = int(season_param)
            except ValueError:
                return Response(
                    {"error": "Invalid season parameter. Must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        need_fetch = False
        try:
            record = PlayerStatList.objects.get(
                league_id=league_id,
                season_id=season_year,
                stat_type=self.stat_type
            )
            if record.updated_at < timezone.now() - timedelta(hours=2):
                need_fetch = True
        except PlayerStatList.DoesNotExist:
            need_fetch = True
            record = None

        if need_fetch:
            from .tasks import fetch_and_update_player_stats
            data = fetch_and_update_player_stats(league_id, season_year, self.stat_type)
            if data is not None:
                record = PlayerStatList.objects.get(
                    league_id=league_id,
                    season_id=season_year,
                    stat_type=self.stat_type
                )
            elif not record:
                return Response(
                    {"error": f"{self.stat_type.replace('top', 'top ')} details not found or failed to retrieve."},
                    status=status.HTTP_404_NOT_FOUND
                )

        serializer = PlayerStatListSerializer(record)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Players'],
    summary="Get Top Scorers",
    parameters=[
        OpenApiParameter(name='league', description='League ID', required=True, type=int),
        OpenApiParameter(name='season', description='Season Year', required=False, type=int)
    ]
)
class TopScorersView(BasePlayerStatListView):
    stat_type = 'topscorers'


@extend_schema(
    tags=['Players'],
    summary="Get Top Assists",
    parameters=[
        OpenApiParameter(name='league', description='League ID', required=True, type=int),
        OpenApiParameter(name='season', description='Season Year', required=False, type=int)
    ]
)
class TopAssistsView(BasePlayerStatListView):
    stat_type = 'topassists'


@extend_schema(
    tags=['Players'],
    summary="Get Top Yellow Cards",
    parameters=[
        OpenApiParameter(name='league', description='League ID', required=True, type=int),
        OpenApiParameter(name='season', description='Season Year', required=False, type=int)
    ]
)
class TopYellowCardsView(BasePlayerStatListView):
    stat_type = 'topyellowcards'


@extend_schema(
    tags=['Players'],
    summary="Get Top Red Cards",
    parameters=[
        OpenApiParameter(name='league', description='League ID', required=True, type=int),
        OpenApiParameter(name='season', description='Season Year', required=False, type=int)
    ]
)
class TopRedCardsView(BasePlayerStatListView):
    stat_type = 'topredcards'


@extend_schema(
    tags=['Teams'],
    summary="Get Team Statistics",
    parameters=[
        OpenApiParameter(name='team', description='Team ID', required=True, type=int),
        OpenApiParameter(name='league', description='League ID', required=True, type=int),
        OpenApiParameter(name='season', description='Season Year', required=False, type=int)
    ]
)
class TeamStatisticsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        team_id = request.query_params.get('team')
        league_id = request.query_params.get('league')
        
        if not team_id or not league_id:
            return Response(
                {"error": "Both team and league parameters are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            team_id = int(team_id)
            league_id = int(league_id)
        except ValueError:
            return Response(
                {"error": "Invalid team or league parameters. Must be integers."},
                status=status.HTTP_400_BAD_REQUEST
            )

        season_param = request.query_params.get('season')
        from django.utils import timezone
        if not season_param:
            current_year = timezone.now().year
            latest_season = Season.objects.filter(year__lte=current_year).order_by('-year').first()
            if not latest_season:
                latest_season = Season.objects.order_by('-year').first()
            season_year = latest_season.year if latest_season else current_year
        else:
            try:
                season_year = int(season_param)
            except ValueError:
                return Response(
                    {"error": "Invalid season parameter. Must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        from datetime import timedelta
        need_fetch = False
        try:
            record = TeamStatistic.objects.get(
                team_id=team_id,
                league_id=league_id,
                season_id=season_year
            )
            if record.updated_at < timezone.now() - timedelta(hours=2):
                need_fetch = True
        except TeamStatistic.DoesNotExist:
            need_fetch = True
            record = None

        if need_fetch:
            from .tasks import fetch_and_update_team_statistics
            data = fetch_and_update_team_statistics(team_id, league_id, season_year)
            if data is not None:
                try:
                    record = TeamStatistic.objects.get(
                        team_id=team_id,
                        league_id=league_id,
                        season_id=season_year
                    )
                except TeamStatistic.DoesNotExist:
                    record = None
            elif not record:
                return Response(
                    {"error": "Team statistics details not found or failed to retrieve."},
                    status=status.HTTP_404_NOT_FOUND
                )

        if not record:
            return Response(
                {"error": "Team statistics details not found or failed to retrieve."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TeamStatisticSerializer(record)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Teams'],
    summary="Get Team Coaches List",
    parameters=[
        OpenApiParameter(name='team', description='Team ID', required=True, type=int)
    ]
)
class CoachsListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        team_id = request.query_params.get('team')
        if not team_id:
            return Response(
                {"error": "team parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            team_id = int(team_id)
        except ValueError:
            return Response(
                {"error": "Invalid team parameter. Must be an integer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        from datetime import timedelta
        from django.utils import timezone
        need_fetch = False
        try:
            record = TeamCoachList.objects.get(team_id=team_id)
            if record.updated_at < timezone.now() - timedelta(days=1):
                need_fetch = True
        except TeamCoachList.DoesNotExist:
            need_fetch = True
            record = None

        if need_fetch:
            from .tasks import fetch_and_update_team_coaches
            data = fetch_and_update_team_coaches(team_id)
            if data is not None:
                try:
                    record = TeamCoachList.objects.get(team_id=team_id)
                except TeamCoachList.DoesNotExist:
                    record = None
            elif not record:
                return Response(
                    {"error": "Coaches details not found or failed to retrieve."},
                    status=status.HTTP_404_NOT_FOUND
                )

        if not record:
            return Response(
                {"error": "Coaches details not found or failed to retrieve."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TeamCoachListSerializer(record)
        return Response(serializer.data, status=status.HTTP_200_OK)