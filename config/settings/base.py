import sys
import os
import environ
from pathlib import Path
from datetime import timedelta

env = environ.Env() # initialize environ
environ.Env.read_env(os.path.join(Path(__file__).resolve().parent.parent.parent, '.env'))

# go up 3 levels: settings -> config -> root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# add apps directory to the path
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))


# Application definition
INSTALLED_APPS = [
    'daphne',

    # django default apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'corsheaders',

    # local apps
    'users',
    'sports',
    'monitoring',
    'notifications.apps.NotificationsConfig',

    # third party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',



    'cloudinary_storage',
    'cloudinary',

    'django_celery_beat',

    'channels',
]



MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    
    'corsheaders.middleware.CorsMiddleware',
    
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'monitoring.middleware.MonitoringMiddleware',
]

ROOT_URLCONF = 'config.urls'

# Database
DATABASES = {
    'default': env.db(
        'DATABASE_URL',
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}'
        )
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# auth user model
AUTH_USER_MODEL = 'users.User'

# DRF Config
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}


# Use BigAutoField as the default primary key field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Cloudinary configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': env('CLOUDINARY_API_KEY'),
    'API_SECRET': env('CLOUDINARY_API_SECRET'),
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
MEDIA_URL = '/media/' 


# --- API KEYS ---
API_FOOTBALL_KEY = env('API_FOOTBALL_KEY')

# --- CELERY CONFIGURATION ---
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Static files 
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


# --- ASGI CONFIG ---
ASGI_APPLICATION = 'config.asgi.application'

# --- CHANNEL LAYERS (Redis) ---
redis_url = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [redis_url],
        },
    },
}

#####
SPECTACULAR_SETTINGS = {
    'TITLE': 'ScoreLivePro API',
    'DESCRIPTION': 'Real-time sports application API documentation',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}


# --- FIREBASE FCM CONFIGURATION ---
FIREBASE_CREDENTIALS_PATH = os.path.join(BASE_DIR, 'firebase-credentials.json')

# Check if Firebase is configured with actual credentials (not placeholders)
FIREBASE_CONFIGURED = False
if os.path.exists(FIREBASE_CREDENTIALS_PATH) and not os.path.isdir(FIREBASE_CREDENTIALS_PATH):
    try:
        import json
        with open(FIREBASE_CREDENTIALS_PATH, 'r') as f:
            creds_data = json.load(f)
            pk = creds_data.get("private_key", "")
            pid = creds_data.get("project_id", "")
            if pk and "YOUR_PRIVATE_KEY_HERE" not in pk and pid and "your-project-id" not in pid:
                FIREBASE_CONFIGURED = True
    except Exception:
        pass


## JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True, 
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': env('SECRET_KEY'), 
    'AUTH_HEADER_TYPES': ('Bearer',),
}

CORS_ALLOW_ALL_ORIGINS = True

# Django Sites framework setting
SITE_ID = 1

