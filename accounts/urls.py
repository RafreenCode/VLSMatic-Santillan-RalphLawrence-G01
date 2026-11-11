from django.http import HttpResponse
from django.urls import path


app_name = "accounts"


def health_check(request):
    return HttpResponse("VLSMatic is ready.", content_type="text/plain")


urlpatterns = [
    path("", health_check, name="home"),
]
