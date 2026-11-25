import os
import subprocess
import sys

from django.conf import settings
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import path
from django.views.defaults import server_error


def broken_view(request):
    raise RuntimeError("private diagnostic must never reach the browser")


# Test-only route: never included in the application's production URL configuration.
urlpatterns = [path("broken/", broken_view)]


@override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False, STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class ErrorPageTests(SimpleTestCase):
    def test_unknown_url_uses_custom_404_without_debug_output(self):
        response = self.client.get("/this-route-does-not-exist/")
        self.assertContains(response, "Page not found", status_code=404)
        self.assertNotContains(response, "URL patterns", status_code=404)

    @override_settings(ROOT_URLCONF=__name__)
    def test_uncaught_error_uses_custom_500_without_traceback(self):
        self.client.raise_request_exception = False
        response = self.client.get("/broken/")
        self.assertContains(response, "Something went wrong", status_code=500)
        self.assertNotContains(response, "private diagnostic", status_code=500)
        self.assertNotContains(response, "Traceback", status_code=500)

    def test_500_template_needs_no_database_or_static_manifest(self):
        response = server_error(RequestFactory().get("/"))
        self.assertContains(response, "Return to VLSMatic", status_code=500)

    def test_debug_false_is_respected_in_local_http_mode(self):
        env = {**os.environ, "APP_ENV": "local", "LOCAL_HTTP": "true", "DEBUG": "false"}
        result = subprocess.run(
            [sys.executable, "-c", "from vlsmatic.settings import DEBUG; print(DEBUG)"],
            cwd=settings.BASE_DIR, env=env, capture_output=True, text=True, check=True,
        )
        self.assertEqual(result.stdout.strip(), "False")
