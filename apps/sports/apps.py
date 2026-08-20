from django.apps import AppConfig
import sys
import os

class SportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sports'

    def ready(self):
        """
        Executed once when the application loads.
        """
        import sports.signals
        
        # 1. Avoid running in the reloader process (runserver spawns two processes)
        # We only want the main process to trigger the task.
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN', None) != 'true':
            return

        # 2. Avoid running during management commands or in celery worker/beat processes
        ignore_commands = ['migrate', 'makemigrations', 'test', 'shell', 'collectstatic', 'check', 'celery']
        if any(cmd in sys.argv for cmd in ignore_commands):
            return

        # 3. Import tasks inside ready() to avoid AppRegistryNotReady errors
        from .tasks import initial_boot_sequence

        print("🚀 ScoreLivePro: Server Ready. Triggering initial boot sequence...")
        
        # 4. Fire the chain
        initial_boot_sequence.delay()
