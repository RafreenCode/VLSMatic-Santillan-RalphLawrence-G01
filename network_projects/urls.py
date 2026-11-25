from django.urls import path

from . import views


app_name = "network_projects"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("new/", views.project_create, name="create"),
    path("<slug:project_slug>/", views.project_detail, name="detail"),
    path("<slug:project_slug>/edit/", views.project_update, name="update"),
    path("<slug:project_slug>/delete/", views.project_delete, name="delete"),
    path("<slug:project_slug>/calculate/", views.project_calculate, name="calculate"),
    path("<slug:project_slug>/subnets/add/", views.requirement_create, name="requirement_create"),
    path("<slug:project_slug>/subnets/<int:requirement_id>/edit/", views.requirement_update, name="requirement_update"),
    path("<slug:project_slug>/subnets/<int:requirement_id>/delete/", views.requirement_delete, name="requirement_delete"),
]
