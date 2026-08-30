import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')

app = Celery('scorelivepro')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # ==================================
    #         REAL-TIME DATA
    # ==================================
    # 1. LIVE SCORES (Ticker) - Every 15s
    'live-score-ticker': {
        'task': 'sports.tasks.update_live_fixtures',
        'schedule': 15.0, 
    },
    
    # 2. LIVE STATISTICS - Every 60s
    'live-statistics-fetcher': {
        'task': 'sports.tasks.fetch_live_statistics',
        'schedule': 60.0, 
    },

    # 3. LINEUPS - Every 15 mins (Checks for new lineups & notifies)
    'lineups-fetcher': {
        'task': 'sports.tasks.fetch_lineups_near_kickoff',
        'schedule': 60.0 * 15,
    },

    # 4. LIVE EVENTS - Every 45s (Cards, Substitutions, VAR for followed matches)
    'live-events-fetcher': {
        'task': 'sports.tasks.fetch_live_events',
        'schedule': 45.0,
    },

    # ==================================
    #      DAILY MAINTENANCE (SAFE)
    # ==================================
    
    # 4. PRIMARY MAINTENANCE CHAIN - 03:00 AM
    # Runs: Countries -> Seasons -> Leagues -> Teams -> Schedule (Sequentially)
    # Replaces all individual midnight tasks to prevent deadlocks.
    'daily-maintenance-seq': {
        'task': 'sports.tasks.daily_maintenance_workflow',
        'schedule': crontab(hour=3, minute=0),
    },

    # 5. H2H WARMUP - 04:30 AM
    # Staggered to run AFTER the main maintenance is likely finished.
    'warmup-h2h-upcoming': {
        'task': 'sports.tasks.warmup_upcoming_h2h',
        'schedule': crontab(hour=4, minute=30),
    },

    # ==================================
    #       NOTIFICATION TASKS
    # ==================================

    # 6. PRE-MATCH ALERTS - Every 15 mins
    'notify-upcoming-matches': {
        'task': 'sports.tasks.check_upcoming_matches_and_notify',
        'schedule': crontab(minute='*/15'),
    },

    # 7. SCHEDULED NOTIFICATIONS - Every 60s
    'process-scheduled-notifications': {
        'task': 'sports.tasks.process_scheduled_notifications',
        'schedule': 60.0, 
    },
    
    # 8. DAILY LEAGUE SCHEDULE - 8:00 AM
    'daily-league-schedule': {
        'task': 'sports.tasks.notify_daily_league_schedule',
        'schedule': crontab(hour=8, minute=0),
    },

    # ==================================
    # ==================================
    #         OTHER UPDATES
    # ==================================
    # Fetches standings every hour (independent read-only mostly, low risk)
    'fetch-standings-frequently': { 
        'task': 'sports.tasks.fetch_standings_hourly', 
        'schedule': crontab(minute='0', hour='*') 
    },

    # CLEANUP STALE FIXTURES - Every 30 mins
    # Force updates matches stuck as live for > 4 hours to finished status
    'cleanup-stale-live-fixtures': {
        'task': 'sports.tasks.cleanup_stale_live_fixtures',
        'schedule': crontab(minute='*/30'),
    },

    # FREQUENT UPCOMING FIXTURES - Every 3 hours
    # Keeps schedule, kickoff times, and statuses fresh for yesterday, today, and tomorrow
    'fetch-upcoming-fixtures-frequent': {
        'task': 'sports.tasks.fetch_upcoming_fixtures',
        'schedule': crontab(minute='0', hour='*/3'),
        'kwargs': {'days': 2, 'include_yesterday': True}
    },

    ########
    'collect-system-metrics': {
        'task': 'monitoring.tasks.collect_system_metrics',
        'schedule': 60.0, # Every minute
    },
}