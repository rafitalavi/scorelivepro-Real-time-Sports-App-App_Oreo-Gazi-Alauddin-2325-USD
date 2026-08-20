from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.setdefault('SECRET_KEY', 'django-insecure-l5tdl19q+t8imusp66ho52ndscqs(qf683@1#y9kgmc#%w((t%')

# default to allow everything if ALLOWED_HOSTS is missing in .env
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])
# ALLOWED_HOSTS = ["*"]

# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')

# Default "From" email
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)