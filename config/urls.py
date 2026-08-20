from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

def app_ads_txt_view(request):
    # REPLACE the string below with your actual AdMob credential string from Google
    admob_content = "google.com, pub-6967886775553979, DIRECT, f08c47fec0942fa0"
    return HttpResponse(admob_content, content_type="text/plain")

urlpatterns = [
    path('admin/', admin.site.urls),



    path('auth/', include('users.urls')),
    path('api/users/', include('users.urls')),
    path('sports/', include('sports.urls')),
    path('api/sports/', include('sports.urls')),
    path('monitoring/', include('monitoring.urls')),
    path('notifications/', include('notifications.urls')),
    path('api/notifications/', include('notifications.urls')),


    # swagger urls
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),    
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # App-ads route
    path('app-ads.txt', app_ads_txt_view, name='app-ads-txt'),
]