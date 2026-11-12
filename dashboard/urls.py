from django.urls import path

from . import views


app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard, name="home"),
    path("user/", views.user_dashboard, name="user"),
    path("administrator/", views.admin_dashboard, name="admin"),
]
