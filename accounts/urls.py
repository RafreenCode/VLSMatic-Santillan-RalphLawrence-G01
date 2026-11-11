from django.urls import path
from django.contrib.auth.views import LogoutView

from . import views


app_name = "accounts"

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.VLSMaticLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/user/", views.user_dashboard, name="user_dashboard"),
    path("dashboard/administrator/", views.admin_dashboard, name="admin_dashboard"),
    path("profile/", views.profile, name="profile"),
]
