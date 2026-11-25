from django.urls import path

from . import views


app_name = "dashboard"

urlpatterns = [
    path("dashboard/", views.dashboard, name="home"),
    path("dashboard/user/", views.user_dashboard, name="user"),
    path("groups/join/", views.user_join_group, name="user_join_group"),
    path("groups/<slug:group_slug>/leave/", views.user_leave_group, name="user_leave_group"),
    path("console/", views.admin_dashboard, name="admin"),
    path("console/groups/", views.admin_group_list, name="admin_group_list"),
    path("console/groups/new/", views.admin_group_create, name="admin_group_create"),
    path("console/groups/<slug:group_slug>/", views.admin_group_detail, name="admin_group_detail"),
    path("console/groups/<slug:group_slug>/edit/", views.admin_group_update, name="admin_group_update"),
    path("console/groups/<slug:group_slug>/delete/", views.admin_group_delete, name="admin_group_delete"),
    path("console/groups/<slug:group_slug>/regenerate-code/", views.admin_group_regenerate_code, name="admin_group_regenerate_code"),
    path("console/groups/<slug:group_slug>/toggle-joinable/", views.admin_group_toggle_joinable, name="admin_group_toggle_joinable"),
    path("console/groups/<slug:group_slug>/members/add/", views.admin_group_add_member, name="admin_group_add_member"),
    path("console/groups/<slug:group_slug>/members/<str:username>/", views.admin_group_member_detail, name="admin_group_member_detail"),
    path("console/groups/<slug:group_slug>/members/<str:username>/remove/", views.admin_group_remove_member, name="admin_group_remove_member"),
    path(
        "console/groups/<slug:group_slug>/members/<str:username>/projects/<slug:project_slug>/",
        views.admin_group_member_project_detail,
        name="admin_group_member_project_detail",
    ),
    path("console/users/", views.admin_user_list, name="admin_user_list"),
    path("console/users/new/", views.admin_user_create, name="admin_user_create"),
    path("console/users/<str:username>/", views.admin_user_detail, name="admin_user_detail"),
    path("console/users/<str:username>/toggle-active/", views.admin_user_toggle_active, name="admin_user_toggle_active"),
    path("console/users/<str:username>/change-role/", views.admin_user_change_role, name="admin_user_change_role"),
    path(
        "console/users/<str:username>/projects/<slug:project_slug>/",
        views.admin_user_project_detail,
        name="admin_user_project_detail",
    ),
]
