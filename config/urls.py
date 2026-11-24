from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf.urls.static import static
from django.conf import settings
from django.http import FileResponse
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework_simplejwt import views as jwt_views


schema_view_v1 = get_schema_view(
   openapi.Info(
      title="Monitoring API V1",
      default_version='v 0.0.1',
      description="Monitoring API v1",
      terms_of_service="https://www.google.com/?hl=ru",
      contact=openapi.Contact(email="info@monitoring.com"),
      license=openapi.License(name="MIT License"),
      
   ),
   public=True,
   permission_classes=(permissions.AllowAny,)
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/swagger/', schema_view_v1.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view_v1.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    path('api/monitoring/', include('monitor.urls')),
    path('api/month-monitor/', include('month_monitor.urls')),
    path('api/authen/', include('authen.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/appleas/', include('appeals.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Add media URLs for serving media files
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT,},),]