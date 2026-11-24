from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('django-admin/', admin.site.urls),      # Django's built-in database admin (optional)
    path('', include('core.urls')),
    # Uploaded profile photos. Fine for a small school project; use cloud storage for big sites.
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
