from django.urls import path

from . import views


app_name = "network_projects"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("new/", views.project_create, name="create"),
    path("<int:project_id>/", views.project_detail, name="detail"),
    path("<int:project_id>/edit/", views.project_update, name="update"),
    path("<int:project_id>/delete/", views.project_delete, name="delete"),
    path("<int:project_id>/requirements/new/", views.requirement_create, name="requirement_create"),
    path("requirements/<int:requirement_id>/edit/", views.requirement_update, name="requirement_update"),
    path("requirements/<int:requirement_id>/delete/", views.requirement_delete, name="requirement_delete"),
]

