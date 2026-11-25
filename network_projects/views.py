from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User, WorkspaceGroup

from .forms import NetworkProjectForm, ProjectFilterForm, SubnetRequirementForm
from .models import NetworkProject, SubnetRequirement
from .services import AllocationError, allocate_project, allocation_visualization, project_summary


def _decorate_projects(projects):
    decorated = list(projects)
    for project in decorated:
        project.total_addresses = 2 ** (32 - project.prefix_length)
        project.allocated_addresses = project.allocated_addresses or 0
        project.address_consumption = project.allocated_addresses / project.total_addresses * 100
        project.plan_status = "Allocated" if project.allocation_count else "Ready to plan"
    return decorated


def _owned_project(request, project_id):
    project = get_object_or_404(NetworkProject, pk=project_id)
    if project.owner_id != request.user.pk:
        if request.user.role == User.Role.ADMIN:
            raise PermissionDenied
        raise Http404
    return project


def _owned_requirement(request, requirement_id):
    requirement = get_object_or_404(
        SubnetRequirement.objects.select_related("project"),
        pk=requirement_id,
    )
    if requirement.project.owner_id != request.user.pk:
        if request.user.role == User.Role.ADMIN:
            raise PermissionDenied
        raise Http404
    return requirement


@login_required
def project_list(request):
    projects = request.user.network_projects.annotate(
        requirement_count=Count("requirements", distinct=True),
        allocation_count=Count("requirements__allocation", distinct=True),
        allocated_addresses=Sum("requirements__allocation__allocated_addresses"),
    )
    filters = ProjectFilterForm(request.GET or None)
    if filters.is_valid():
        if filters.cleaned_data["name"]:
            projects = projects.filter(name__icontains=filters.cleaned_data["name"])
        if filters.cleaned_data["network"]:
            projects = projects.filter(base_network=filters.cleaned_data["network"])
        if filters.cleaned_data["created_date"]:
            projects = projects.filter(created_at__date=filters.cleaned_data["created_date"])
    return render(
        request,
        "network_projects/project_list.html",
        {"projects": _decorate_projects(projects), "filters": filters, "filters_active": bool(request.GET)},
    )


@login_required
def project_create(request):
    form = NetworkProjectForm(request.POST or None, owner=request.user)
    if request.method == "POST" and form.is_valid():
        project = form.save(commit=False)
        project.owner = request.user
        project.save()
        messages.success(request, "Project created successfully.")
        return redirect("network_projects:detail", project_id=project.pk)
    return render(request, "network_projects/project_form.html", {"form": form, "heading": "Create a network project"})


@login_required
def project_detail(request, project_id):
    source_group = None
    if request.user.role == User.Role.ADMIN:
        project = get_object_or_404(NetworkProject.objects.select_related("owner"), pk=project_id)
        read_only = project.owner_id != request.user.pk
        if read_only:
            group_id = request.GET.get("group", "").strip()
            if group_id.isdigit():
                source_group = WorkspaceGroup.objects.filter(
                    pk=int(group_id), memberships__user=project.owner
                ).first()
    else:
        project = _owned_project(request, project_id)
        read_only = False
    requirements = list(project.requirements.select_related("allocation").all())
    studio_warning = request.session.pop("studio_warning", None)
    return render(
        request,
        "network_projects/project_detail.html",
        {
            "project": project,
            "requirements": requirements,
            "summary": project_summary(project, requirements),
            "visualization_data": allocation_visualization(project, requirements),
            "read_only": read_only,
            "source_group": source_group,
            "studio_warning": studio_warning,
        },
    )


def _flash_studio_warning(request, title, form, extra=None):
    error_messages = []
    for field_errors in form.errors.values():
        error_messages.extend(str(err) for err in field_errors)
    payload = {
        "title": title,
        "messages": error_messages or ["Please check your input and try again."],
    }
    if extra:
        payload.update(extra)
    request.session["studio_warning"] = payload


@login_required
def project_update(request, project_id):
    project = _owned_project(request, project_id)
    if request.method != "POST":
        return redirect("network_projects:detail", project_id=project.pk)
    original_network = (project.base_network, project.prefix_length)
    form = NetworkProjectForm(request.POST, instance=project, owner=request.user)
    if form.is_valid():
        network_changed = original_network != (
            form.cleaned_data["base_network"],
            form.cleaned_data["prefix_length"],
        )
        try:
            with transaction.atomic():
                project = form.save()
                if network_changed and project.requirements.exists():
                    allocate_project(project)
        except AllocationError as error:
            form.add_error(None, error.messages[0])
        else:
            messages.success(request, "Project updated and its allocation recalculated.")
            return redirect("network_projects:detail", project_id=project.pk)
    _flash_studio_warning(request, "Could not update project boundary", form)
    return redirect("network_projects:detail", project_id=project.pk)


@login_required
def project_delete(request, project_id):
    project = _owned_project(request, project_id)
    if request.method == "POST":
        project.delete()
        messages.success(request, "Project deleted.")
        return redirect("network_projects:list")
    return redirect("network_projects:detail", project_id=project.pk)


@login_required
def requirement_create(request, project_id):
    project = _owned_project(request, project_id)
    if request.method != "POST":
        return redirect("network_projects:detail", project_id=project.pk)
    form = SubnetRequirementForm(request.POST, project=project)
    if form.is_valid():
        try:
            with transaction.atomic():
                requirement = form.save(commit=False)
                requirement.project = project
                requirement.sort_order = project.requirements.count()
                requirement.save()
                allocate_project(project)
        except AllocationError as error:
            form.add_error(None, error.messages[0])
        else:
            messages.success(request, "Subnet requirement added and the plan recalculated.")
            return redirect("network_projects:detail", project_id=project.pk)
    _flash_studio_warning(
        request,
        "Could not add subnet",
        form,
        extra={
            "name": request.POST.get("name", ""),
            "required_hosts": request.POST.get("required_hosts", ""),
        },
    )
    return redirect("network_projects:detail", project_id=project.pk)


@login_required
def requirement_update(request, requirement_id):
    requirement = _owned_requirement(request, requirement_id)
    if request.method != "POST":
        return redirect("network_projects:detail", project_id=requirement.project_id)
    form = SubnetRequirementForm(request.POST, instance=requirement, project=requirement.project)
    if form.is_valid():
        try:
            with transaction.atomic():
                form.save()
                allocate_project(requirement.project)
        except AllocationError as error:
            form.add_error(None, error.messages[0])
        else:
            messages.success(request, "Subnet requirement updated and the plan recalculated.")
            return redirect("network_projects:detail", project_id=requirement.project_id)
    _flash_studio_warning(request, f"Could not update {requirement.name}", form)
    return redirect("network_projects:detail", project_id=requirement.project_id)


@login_required
def requirement_delete(request, requirement_id):
    requirement = _owned_requirement(request, requirement_id)
    project = requirement.project
    if request.method == "POST":
        with transaction.atomic():
            requirement.delete()
            allocate_project(project, allow_empty=True)
        messages.success(request, "Subnet requirement deleted and the plan recalculated.")
    return redirect("network_projects:detail", project_id=project.pk)


@login_required
@require_POST
def project_calculate(request, project_id):
    project = _owned_project(request, project_id)
    try:
        allocate_project(project)
    except AllocationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, "Allocation generated successfully.")
    return redirect("network_projects:detail", project_id=project.pk)
