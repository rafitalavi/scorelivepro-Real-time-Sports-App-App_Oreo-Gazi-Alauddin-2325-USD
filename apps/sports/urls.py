from django.urls import path
from .views import (
    FixtureHeadToHeadView, FixtureWebSocketDocsView, TimezoneListView, SeasonListView, CountryListView, LeagueListView, LeagueDetailView,
    TeamListView, TeamDetailView, VenueListView, StandingListView, StandingDetailView,
    TeamCountryGroupedView,
    FixtureListView, FixtureDetailView, FixtureLineupsView, FixtureStatisticsView, PlayerDetailView,
    TopScorersView, TopAssistsView, TopYellowCardsView, TopRedCardsView,
    TeamStatisticsView, CoachsListView
)

urlpatterns = [
    # DOCUMENTATION ONLY ROUTE
    path('ws/live/', FixtureWebSocketDocsView.as_view(), name='ws-live-docs'),

    path('timezones/', TimezoneListView.as_view(), name='timezone-list'),   
    path('countries/', CountryListView.as_view(), name='country-list'),
    path('seasons/', SeasonListView.as_view(), name='season-list'),
    
    path('leagues/', LeagueListView.as_view(), name='league-list'),
    path('leagues/<int:pk>/', LeagueDetailView.as_view(), name='league-detail'),
    
    path('teams/country-grouped/', TeamCountryGroupedView.as_view(), name='team-country-grouped'),
    path('teams/', TeamListView.as_view(), name='team-list'),
    path('teams/<int:pk>/', TeamDetailView.as_view(), name='team-detail'),
    path('teams/statistics/', TeamStatisticsView.as_view(), name='team-statistics'),
    path('coachs/', CoachsListView.as_view(), name='coachs-list'),
    path('players/<int:pk>/', PlayerDetailView.as_view(), name='player-detail'),
    path('players/topscorers/', TopScorersView.as_view(), name='topscorers'),
    path('players/topassists/', TopAssistsView.as_view(), name='topassists'),
    path('players/topyellowcards/', TopYellowCardsView.as_view(), name='topyellowcards'),
    path('players/topredcards/', TopRedCardsView.as_view(), name='topredcards'),
    
    path('venues/', VenueListView.as_view(), name='venue-list'),
    
    path('standings/', StandingListView.as_view(), name='standing-list'),
    path('standings/<int:league_id>/<int:season_year>/', StandingDetailView.as_view(), name='standing-detail'),

    # Fixtures
    path('fixtures/', FixtureListView.as_view(), name='fixture-list'),
    path('fixtures/<int:pk>/', FixtureDetailView.as_view(), name='fixture-detail'),
    
    path('fixtures/<int:pk>/lineups/', FixtureLineupsView.as_view(), name='fixture-lineups'),
    path('fixtures/<int:pk>/statistics/', FixtureStatisticsView.as_view(), name='fixture-statistics'),    
    path('fixtures/<int:pk>/h2h/', FixtureHeadToHeadView.as_view(), name='fixture-h2h'),
]