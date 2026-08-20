import sys
import os
from django.apps import AppConfig
from django.conf import settings
import firebase_admin
from firebase_admin import credentials


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        # prevent initialization during migrations/tests
        # if 'runserver' not in sys.argv and 'gunicorn' not in sys.argv:
        #     return
        
        # initialize Firebase Admin SDK
        if not firebase_admin._apps:
            if getattr(settings, 'FIREBASE_CONFIGURED', False):
                try:
                    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                    firebase_admin.initialize_app(cred)
                    print("Firebase Admin SDK Initialized in Notifications App")
                except Exception as e:
                    print(f"Firebase Initialization Failed: {e}")
            else:
                print("Firebase Admin SDK running in Simulator Mode (missing or placeholder credentials)")