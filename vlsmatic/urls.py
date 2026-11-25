from django.conf import settings
from django.conf.urls.static import static
from django.templatetags.static import static as static_url
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url=static_url("img/favicon.ico"), permanent=False)),
    path("admin/login/", RedirectView.as_view(pattern_name="dashboard:admin", permanent=False)),
    path("admin/", RedirectView.as_view(pattern_name="dashboard:admin", permanent=False)),
    path("projects/", include("network_projects.urls")),
    path("", include("dashboard.urls")),
    path("", include("accounts.urls")),
]

if settings.DEBUG and settings.PROFILE_PHOTO_STORAGE == "local":
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
