from django.urls import path

from . import views


app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard, name="home"),
    path("user/", views.user_dashboard, name="user"),
    path("user/groups/join/", views.user_join_group, name="user_join_group"),
    path("user/groups/<int:group_id>/leave/", views.user_leave_group, name="user_leave_group"),
    path("administrator/", views.admin_dashboard, name="admin"),
    path("administrator/groups/", views.admin_group_list, name="admin_group_list"),
    path("administrator/groups/create/", views.admin_group_create, name="admin_group_create"),
    path("administrator/groups/<int:group_id>/", views.admin_group_detail, name="admin_group_detail"),
    path("administrator/groups/<int:group_id>/edit/", views.admin_group_update, name="admin_group_update"),
    path("administrator/groups/<int:group_id>/delete/", views.admin_group_delete, name="admin_group_delete"),
    path("administrator/groups/<int:group_id>/regenerate-code/", views.admin_group_regenerate_code, name="admin_group_regenerate_code"),
    path("administrator/groups/<int:group_id>/toggle-joinable/", views.admin_group_toggle_joinable, name="admin_group_toggle_joinable"),
    path("administrator/groups/<int:group_id>/members/add/", views.admin_group_add_member, name="admin_group_add_member"),
    path("administrator/groups/<int:group_id>/members/<int:user_id>/remove/", views.admin_group_remove_member, name="admin_group_remove_member"),
    path("administrator/users/", views.admin_user_list, name="admin_user_list"),
    path("administrator/users/create/", views.admin_user_create, name="admin_user_create"),
    path("administrator/users/<int:user_id>/", views.admin_user_detail, name="admin_user_detail"),
    path("administrator/users/<int:user_id>/toggle-active/", views.admin_user_toggle_active, name="admin_user_toggle_active"),
    path("administrator/users/<int:user_id>/change-role/", views.admin_user_change_role, name="admin_user_change_role"),
]
