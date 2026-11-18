from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User

from .forms import NetworkProjectForm, SubnetRequirementForm
from .models import NetworkProject, SubnetRequirement


def _owned_project(request, project_id):
    if request.user.role != User.Role.USER:
        raise PermissionDenied
    return get_object_or_404(NetworkProject, pk=project_id, owner=request.user)


def _owned_requirement(request, requirement_id):
    if request.user.role != User.Role.USER:
        raise PermissionDenied
    return get_object_or_404(
        SubnetRequirement.objects.select_related("project"),
        pk=requirement_id,
        project__owner=request.user,
    )


def _clear_project_allocations(project):
    project.requirements.update(
        network_address=None,
        prefix_length=None,
        subnet_mask=None,
        first_usable_address=None,
        last_usable_address=None,
        broadcast_address=None,
        allocated_capacity=None,
    )


@login_required
def project_list(request):
    if request.user.role == User.Role.ADMIN:
        projects = NetworkProject.objects.select_related("owner").annotate(requirement_count=Count("requirements"))
        return render(request, "network_projects/admin_project_list.html", {"projects": projects})
    projects = request.user.network_projects.annotate(requirement_count=Count("requirements"))
    return render(request, "network_projects/project_list.html", {"projects": projects})


@login_required
def project_create(request):
    if request.user.role != User.Role.USER:
        return redirect("network_projects:list")
    form = NetworkProjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        project = form.save(commit=False)
        project.owner = request.user
        project.save()
        messages.success(request, "Project created successfully.")
        return redirect("network_projects:detail", project_id=project.pk)
    return render(request, "network_projects/project_form.html", {"form": form, "heading": "Create a network project"})


@login_required
def project_detail(request, project_id):
    if request.user.role == User.Role.ADMIN:
        project = get_object_or_404(NetworkProject.objects.select_related("owner"), pk=project_id)
        read_only = True
    else:
        project = _owned_project(request, project_id)
        read_only = False
    return render(
        request,
        "network_projects/project_detail.html",
        {"project": project, "requirements": project.requirements.all(), "read_only": read_only},
    )


@login_required
def project_update(request, project_id):
    project = _owned_project(request, project_id)
    original_network = (project.base_network, project.prefix_length)
    form = NetworkProjectForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        network_changed = original_network != (
            form.cleaned_data["base_network"],
            form.cleaned_data["prefix_length"],
        )
        project = form.save()
        if network_changed:
            _clear_project_allocations(project)
        messages.success(request, "Project updated. Generate the allocation again if its network changed.")
        return redirect("network_projects:detail", project_id=project.pk)
    return render(request, "network_projects/project_form.html", {"form": form, "project": project, "heading": "Edit project"})


@login_required
def project_delete(request, project_id):
    project = _owned_project(request, project_id)
    if request.method == "POST":
        project.delete()
        messages.success(request, "Project deleted.")
        return redirect("network_projects:list")
    return render(request, "network_projects/project_confirm_delete.html", {"project": project})


@login_required
def requirement_create(request, project_id):
    project = _owned_project(request, project_id)
    form = SubnetRequirementForm(request.POST or None, project=project)
    if request.method == "POST" and form.is_valid():
        requirement = form.save(commit=False)
        requirement.project = project
        requirement.sort_order = project.requirements.count()
        requirement.save()
        _clear_project_allocations(project)
        messages.success(request, "Subnet requirement added.")
        return redirect("network_projects:detail", project_id=project.pk)
    return render(request, "network_projects/requirement_form.html", {"form": form, "project": project, "heading": "Add a subnet requirement"})


@login_required
def requirement_update(request, requirement_id):
    requirement = _owned_requirement(request, requirement_id)
    form = SubnetRequirementForm(request.POST or None, instance=requirement, project=requirement.project)
    if request.method == "POST" and form.is_valid():
        form.save()
        _clear_project_allocations(requirement.project)
        messages.success(request, "Subnet requirement updated.")
        return redirect("network_projects:detail", project_id=requirement.project_id)
    return render(request, "network_projects/requirement_form.html", {"form": form, "project": requirement.project, "requirement": requirement, "heading": "Edit subnet requirement"})


@login_required
def requirement_delete(request, requirement_id):
    requirement = _owned_requirement(request, requirement_id)
    project = requirement.project
    if request.method == "POST":
        requirement.delete()
        _clear_project_allocations(project)
        messages.success(request, "Subnet requirement deleted.")
        return redirect("network_projects:detail", project_id=project.pk)
    return render(request, "network_projects/requirement_confirm_delete.html", {"requirement": requirement, "project": project})
