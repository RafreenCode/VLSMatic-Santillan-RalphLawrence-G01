from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.integrity import is_unique_conflict
from dashboard.decorators import role_required

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


def _owned_project(request, project_slug, *, lock=False):
    projects = NetworkProject.objects.select_for_update() if lock else NetworkProject.objects.all()
    project = get_object_or_404(projects, slug=project_slug)
    if project.owner_id != request.user.pk:
        if request.user.role == User.Role.ADMIN:
            raise PermissionDenied
        raise Http404
    return project


def _owned_requirement(request, project_slug, requirement_id):
    # Every mutation locks the parent first, matching the allocator's lock order.
    project = _owned_project(request, project_slug, lock=True)
    requirement = get_object_or_404(SubnetRequirement, pk=requirement_id, project=project)
    requirement.project = project
    return requirement


def _save_error(form, error):
    if isinstance(error, IntegrityError):
        if not is_unique_conflict(error):
            raise error
        form.add_error(None, "A record with this name was just saved. Refresh and use a different name.")
    else:
        form.add_error(None, ValidationError(error.messages))


def render_project_studio(request, project, *, read_only: bool, source_group=None):
    requirements = list(project.requirements.select_related("allocation").all())
    studio_warning = None if read_only else request.session.pop("studio_warning", None)
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


@role_required(User.Role.USER, User.Role.ADMIN)
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


@role_required(User.Role.USER, User.Role.ADMIN)
@transaction.atomic
def project_create(request):
    if request.method == "POST":
        # Serialize per-owner name checks, including a repeated submission.
        User.objects.select_for_update().get(pk=request.user.pk)
    form = NetworkProjectForm(request.POST if request.method == "POST" else None, owner=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                project = form.save(commit=False)
                project.owner = request.user
                project.save()
        except (ValidationError, IntegrityError) as error:
            _save_error(form, error)
        else:
            messages.success(request, "Project created successfully.")
            return redirect("network_projects:detail", project_slug=project.slug)
    return render(request, "network_projects/project_form.html", {"form": form, "heading": "Create a network project"})


@role_required(User.Role.USER, User.Role.ADMIN)
def project_detail(request, project_slug):
    project = get_object_or_404(NetworkProject.objects.select_related("owner"), slug=project_slug)
    if project.owner_id != request.user.pk:
        if request.user.role == User.Role.ADMIN:
            return redirect(
                "dashboard:admin_user_project_detail",
                username=project.owner.username,
                project_slug=project.slug,
            )
        raise Http404
    return render_project_studio(request, project, read_only=False)


@role_required(User.Role.USER, User.Role.ADMIN)
@require_POST
@transaction.atomic
def project_update(request, project_slug):
    User.objects.select_for_update().get(pk=request.user.pk)
    project = _owned_project(request, project_slug, lock=True)
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
        except (ValidationError, IntegrityError) as error:
            _save_error(form, error)
        else:
            messages.success(request, "Project updated and its allocation recalculated.")
            return redirect("network_projects:detail", project_slug=project.slug)
    _flash_studio_warning(request, "Could not update project boundary", form)
    return redirect("network_projects:detail", project_slug=project.slug)


@role_required(User.Role.USER, User.Role.ADMIN)
@require_POST
@transaction.atomic
def project_delete(request, project_slug):
    project = _owned_project(request, project_slug, lock=True)
    project.delete()
    messages.success(request, "Project deleted.")
    return redirect("network_projects:list")


@role_required(User.Role.USER, User.Role.ADMIN)
@require_POST
@transaction.atomic
def requirement_create(request, project_slug):
    project = _owned_project(request, project_slug, lock=True)
    form = SubnetRequirementForm(request.POST, project=project)
    if form.is_valid():
        try:
            with transaction.atomic():
                requirement = form.save(commit=False)
                requirement.project = project
                requirement.sort_order = project.requirements.count()
                requirement.save()
                allocate_project(project)
        except (ValidationError, IntegrityError) as error:
            _save_error(form, error)
        else:
            messages.success(request, "Subnet requirement added and the plan recalculated.")
            return redirect("network_projects:detail", project_slug=project.slug)
    _flash_studio_warning(
        request,
        "Could not add subnet",
        form,
        extra={
            "name": request.POST.get("name", ""),
            "required_hosts": request.POST.get("required_hosts", ""),
        },
    )
    return redirect("network_projects:detail", project_slug=project.slug)


@role_required(User.Role.USER, User.Role.ADMIN)
@require_POST
@transaction.atomic
def requirement_update(request, project_slug, requirement_id):
    requirement = _owned_requirement(request, project_slug, requirement_id)
    form = SubnetRequirementForm(request.POST, instance=requirement, project=requirement.project)
    if form.is_valid():
        try:
            with transaction.atomic():
                form.save()
                allocate_project(requirement.project)
        except (ValidationError, IntegrityError) as error:
            _save_error(form, error)
        else:
            messages.success(request, "Subnet requirement updated and the plan recalculated.")
            return redirect("network_projects:detail", project_slug=requirement.project.slug)
    _flash_studio_warning(request, f"Could not update {requirement.name}", form)
    return redirect("network_projects:detail", project_slug=requirement.project.slug)


@role_required(User.Role.USER, User.Role.ADMIN)
@require_POST
@transaction.atomic
def requirement_delete(request, project_slug, requirement_id):
    requirement = _owned_requirement(request, project_slug, requirement_id)
    project = requirement.project
    try:
        with transaction.atomic():
            requirement.delete()
            allocate_project(project, allow_empty=True)
    except AllocationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, "Subnet requirement deleted and the plan recalculated.")
    return redirect("network_projects:detail", project_slug=project.slug)


@role_required(User.Role.USER, User.Role.ADMIN)
@require_POST
@transaction.atomic
def project_calculate(request, project_slug):
    project = _owned_project(request, project_slug, lock=True)
    try:
        allocate_project(project)
    except AllocationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, "Allocation generated successfully.")
    return redirect("network_projects:detail", project_slug=project.slug)
