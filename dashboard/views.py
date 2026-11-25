from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import GroupMembership, User, WorkspaceGroup
from network_projects.models import NetworkProject, SubnetRequirement
from network_projects.services import allocation_visualization, project_summary

from .decorators import role_required
from .forms import (
    AdminGroupAddMemberForm,
    AdminUserCreateForm,
    AdminUserFilterForm,
    AdminUserUpdateForm,
    JoinGroupCodeForm,
    WorkspaceGroupForm,
)


def _decorate_admin_projects(projects):
    decorated = list(projects)
    for project in decorated:
        project.allocated_addresses = project.allocated_addresses or 0
        project.total_addresses = 2 ** (32 - project.prefix_length)
        project.address_consumption = project.allocated_addresses / project.total_addresses * 100
        project.plan_status = "Allocated" if project.allocation_count else "Ready to plan"
    return decorated


def _is_last_active_admin(target_user):
    if target_user.role != User.Role.ADMIN or not target_user.is_active:
        return False
    return User.objects.filter(role_record_id=User.Role.ADMIN, is_active=True).exclude(pk=target_user.pk).count() == 0


def _admin_tab_context(active_tab: str) -> dict:
    return {
        "admin_active_tab": active_tab,
        "admin_group_count": WorkspaceGroup.objects.count(),
        "admin_user_count": User.objects.count(),
        "admin_project_count": NetworkProject.objects.count(),
    }


def _filter_users_queryset(request):
    user_filters = AdminUserFilterForm(request.GET or None)
    users_qs = (
        User.objects.select_related("role_record")
        .prefetch_related("workspace_groups")
        .annotate(
            project_count=Count("network_projects", distinct=True),
            allocated_addresses=Sum("network_projects__requirements__allocation__allocated_addresses"),
        )
        .order_by("-is_active", "role_record_id", "username")
    )
    if user_filters.is_valid():
        query = user_filters.cleaned_data.get("q", "").strip()
        group_val = user_filters.cleaned_data.get("group", "")
        role = user_filters.cleaned_data.get("role", "")
        status = user_filters.cleaned_data.get("status", "")
        if query:
            users_qs = users_qs.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )
        if group_val == "unassigned":
            users_qs = users_qs.filter(group_memberships__isnull=True)
        elif group_val.isdigit():
            users_qs = users_qs.filter(group_memberships__group_id=int(group_val))
        if role:
            users_qs = users_qs.filter(role_record_id=role)
        if status == "active":
            users_qs = users_qs.filter(is_active=True)
        elif status == "inactive":
            users_qs = users_qs.filter(is_active=False)

    users = list(users_qs)
    for account in users:
        account.allocated_addresses = account.allocated_addresses or 0
    filters_active = any(request.GET.get(k) for k in ("q", "group", "role", "status"))
    return users, user_filters, filters_active


@login_required
def dashboard(request):
    if request.user.role == User.Role.ADMIN:
        return redirect("dashboard:admin")
    return redirect("dashboard:user")


@role_required(User.Role.USER)
def user_dashboard(request):
    projects = request.user.network_projects.annotate(
        requirement_count=Count("requirements", distinct=True),
        allocation_count=Count("requirements__allocation", distinct=True),
        allocated_addresses=Sum("requirements__allocation__allocated_addresses"),
    )
    recent_projects = list(projects.prefetch_related("requirements__allocation")[:4])
    dashboard_plans_data = []
    for project in recent_projects:
        project.allocated_addresses = project.allocated_addresses or 0
        project.total_addresses = 2 ** (32 - project.prefix_length)
        project.address_consumption = project.allocated_addresses / project.total_addresses * 100
        project.plan_status = "Allocated" if project.allocation_count else "Ready to plan"
        requirements = list(project.requirements.all())
        summary = project_summary(project, requirements)
        allocations = allocation_visualization(project, requirements)
        dashboard_plans_data.append(
            {
                "id": project.pk,
                "name": project.name,
                "cidr": project.cidr,
                "detail_url": reverse("network_projects:detail", args=[project.pk]),
                "summary": summary,
                "allocations": allocations,
            }
        )

    resume_project = next(
        (project for project in recent_projects if project.allocation_count),
        recent_projects[0] if recent_projects else None,
    )
    resume_summary = None
    resume_visualization = []
    resume_first_allocation = None
    if resume_project:
        matched = next((item for item in dashboard_plans_data if item["id"] == resume_project.pk), None)
        if matched:
            resume_summary = matched["summary"]
            resume_visualization = matched["allocations"]
            resume_first_allocation = resume_visualization[0] if resume_visualization else None

    connected_memberships = list(
        request.user.group_memberships.select_related("group", "group__created_by").order_by("group__name")
    )

    return render(
        request,
        "dashboard/user.html",
        {
            "project_count": projects.count(),
            "subnet_count": request.user.network_projects.aggregate(total=Count("requirements"))["total"],
            "active_plan_count": projects.filter(calculation_run__isnull=False).count(),
            "allocated_address_count": projects.aggregate(
                total=Sum("requirements__allocation__allocated_addresses")
            )["total"]
            or 0,
            "recent_projects": recent_projects,
            "resume_project": resume_project,
            "resume_summary": resume_summary,
            "resume_visualization": resume_visualization,
            "resume_first_allocation": resume_first_allocation,
            "dashboard_plans_data": dashboard_plans_data,
            "connected_memberships": connected_memberships,
            "join_group_form": JoinGroupCodeForm(),
        },
    )


@role_required(User.Role.USER)
@require_POST
def user_join_group(request):
    form = JoinGroupCodeForm(request.POST)
    if not form.is_valid():
        messages.error(request, form.errors["join_code"][0])
        return redirect("dashboard:user")

    code = form.cleaned_data["join_code"]
    group = WorkspaceGroup.objects.filter(join_code=code).first()
    if group is None:
        messages.error(request, f"No group matched join code {code}. Check the code and try again.")
        return redirect("dashboard:user")
    if not group.is_joinable:
        messages.error(request, f'Group "{group.name}" is currently paused for new members.')
        return redirect("dashboard:user")

    _, created = GroupMembership.objects.get_or_create(group=group, user=request.user)
    if created:
        messages.success(request, f'Connected to group "{group.name}".')
    else:
        messages.info(request, f'You are already a member of "{group.name}".')
    return redirect("dashboard:user")


@role_required(User.Role.USER)
@require_POST
def user_leave_group(request, group_id):
    membership = get_object_or_404(GroupMembership.objects.select_related("group"), group_id=group_id, user=request.user)
    group_name = membership.group.name
    membership.delete()
    messages.success(request, f'Left group "{group_name}".')
    return redirect("dashboard:user")


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    users, user_filters, user_filters_active = _filter_users_queryset(request)
    groups = list(
        WorkspaceGroup.objects.select_related("created_by")
        .annotate(
            member_count=Count("memberships", distinct=True),
            project_count=Count("members__network_projects", distinct=True),
        )
        .order_by("name")[:6]
    )
    recent_qs = NetworkProject.objects.select_related("owner").annotate(
        requirement_count=Count("requirements", distinct=True),
        allocation_count=Count("requirements__allocation", distinct=True),
        allocated_addresses=Sum("requirements__allocation__allocated_addresses"),
    )[:6]

    context = {
        **_admin_tab_context("overview"),
        "total_groups": WorkspaceGroup.objects.count(),
        "total_users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "total_projects": NetworkProject.objects.count(),
        "total_requirements": SubnetRequirement.objects.count(),
        "total_allocations": SubnetRequirement.objects.filter(allocation__isnull=False).count(),
        "groups": groups,
        "users": users,
        "user_filters": user_filters,
        "user_filters_active": user_filters_active,
        "recent_projects": _decorate_admin_projects(recent_qs),
    }
    return render(request, "dashboard/admin.html", context)


@role_required(User.Role.ADMIN)
def admin_group_list(request):
    query = request.GET.get("q", "").strip()
    groups_qs = WorkspaceGroup.objects.select_related("created_by").annotate(
        member_count=Count("memberships", distinct=True),
        project_count=Count("members__network_projects", distinct=True),
    )
    if query:
        groups_qs = groups_qs.filter(
            Q(name__icontains=query) | Q(description__icontains=query) | Q(join_code__icontains=query)
        )
    context = {
        **_admin_tab_context("groups"),
        "groups": list(groups_qs),
        "search_query": query,
    }
    return render(request, "dashboard/admin_group_list.html", context)


@role_required(User.Role.ADMIN)
def admin_group_create(request):
    form = WorkspaceGroupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        group = form.save(commit=False)
        group.created_by = request.user
        group.join_code = WorkspaceGroup.generate_unique_join_code()
        group.save()
        messages.success(request, f'Group "{group.name}" created with join code {group.join_code}.')
        return redirect("dashboard:admin_group_detail", group_id=group.pk)
    return render(
        request,
        "dashboard/admin_group_form.html",
        {**_admin_tab_context("groups"), "form": form, "editing": False},
    )


@role_required(User.Role.ADMIN)
def admin_group_detail(request, group_id):
    group = get_object_or_404(WorkspaceGroup.objects.select_related("created_by"), pk=group_id)
    member_query = request.GET.get("q", "").strip()

    memberships_qs = (
        group.memberships.select_related("user", "user__role_record", "added_by")
        .annotate(
            project_count=Count("user__network_projects", distinct=True),
            allocated_addresses=Sum("user__network_projects__requirements__allocation__allocated_addresses"),
        )
        .order_by("user__username")
    )
    if member_query:
        memberships_qs = memberships_qs.filter(
            Q(user__username__icontains=member_query)
            | Q(user__email__icontains=member_query)
            | Q(user__first_name__icontains=member_query)
            | Q(user__last_name__icontains=member_query)
        )
    memberships = list(memberships_qs)
    for membership in memberships:
        membership.allocated_addresses = membership.allocated_addresses or 0

    group_projects_qs = (
        NetworkProject.objects.filter(owner__group_memberships__group=group)
        .select_related("owner")
        .annotate(
            requirement_count=Count("requirements", distinct=True),
            allocation_count=Count("requirements__allocation", distinct=True),
            allocated_addresses=Sum("requirements__allocation__allocated_addresses"),
        )
        .distinct()
        .order_by("-updated_at")
    )
    group_projects = _decorate_admin_projects(group_projects_qs)

    return render(
        request,
        "dashboard/admin_group_detail.html",
        {
            **_admin_tab_context("groups"),
            "group": group,
            "memberships": memberships,
            "group_projects": group_projects,
            "add_member_form": AdminGroupAddMemberForm(group=group),
            "member_query": member_query,
        },
    )


@role_required(User.Role.ADMIN)
def admin_group_update(request, group_id):
    group = get_object_or_404(WorkspaceGroup, pk=group_id)
    form = WorkspaceGroupForm(request.POST or None, instance=group)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f'Updated group "{group.name}".')
        return redirect("dashboard:admin_group_detail", group_id=group.pk)
    return render(
        request,
        "dashboard/admin_group_form.html",
        {**_admin_tab_context("groups"), "form": form, "group": group, "editing": True},
    )


@role_required(User.Role.ADMIN)
@require_POST
def admin_group_delete(request, group_id):
    group = get_object_or_404(WorkspaceGroup, pk=group_id)
    name = group.name
    group.delete()
    messages.success(request, f'Deleted group "{name}".')
    return redirect("dashboard:admin_group_list")


@role_required(User.Role.ADMIN)
@require_POST
def admin_group_regenerate_code(request, group_id):
    group = get_object_or_404(WorkspaceGroup, pk=group_id)
    new_code = group.regenerate_join_code()
    messages.success(request, f'Generated new join code {new_code} for "{group.name}".')
    return redirect("dashboard:admin_group_detail", group_id=group.pk)


@role_required(User.Role.ADMIN)
@require_POST
def admin_group_toggle_joinable(request, group_id):
    group = get_object_or_404(WorkspaceGroup, pk=group_id)
    group.is_joinable = not group.is_joinable
    group.save(update_fields=["is_joinable", "updated_at"])
    state = "reopened" if group.is_joinable else "paused"
    messages.success(request, f'Joining for "{group.name}" has been {state}.')
    return redirect("dashboard:admin_group_detail", group_id=group.pk)


@role_required(User.Role.ADMIN)
@require_POST
def admin_group_add_member(request, group_id):
    group = get_object_or_404(WorkspaceGroup, pk=group_id)
    form = AdminGroupAddMemberForm(request.POST, group=group)
    if form.is_valid():
        member = form.cleaned_data["user"]
        GroupMembership.objects.get_or_create(group=group, user=member, defaults={"added_by": request.user})
        messages.success(request, f'Added @{member.username} to "{group.name}".')
    else:
        messages.error(request, "Select a valid user to add to this group.")
    return redirect("dashboard:admin_group_detail", group_id=group.pk)


@role_required(User.Role.ADMIN)
@require_POST
def admin_group_remove_member(request, group_id, user_id):
    group = get_object_or_404(WorkspaceGroup, pk=group_id)
    membership = get_object_or_404(GroupMembership.objects.select_related("user"), group=group, user_id=user_id)
    username = membership.user.username
    membership.delete()
    messages.success(request, f'Removed @{username} from "{group.name}".')
    return redirect("dashboard:admin_group_detail", group_id=group.pk)


@role_required(User.Role.ADMIN)
def admin_user_list(request):
    users, user_filters, user_filters_active = _filter_users_queryset(request)
    return render(
        request,
        "dashboard/admin_user_list.html",
        {
            **_admin_tab_context("users"),
            "users": users,
            "user_filters": user_filters,
            "user_filters_active": user_filters_active,
        },
    )


@role_required(User.Role.ADMIN)
def admin_user_create(request):
    form = AdminUserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        new_user = form.save()
        messages.success(request, f"Account @{new_user.username} was created.")
        return redirect("dashboard:admin_user_detail", user_id=new_user.pk)
    return render(request, "dashboard/admin_user_form.html", {**_admin_tab_context("users"), "form": form})


@role_required(User.Role.ADMIN)
def admin_user_detail(request, user_id):
    target_user = get_object_or_404(User.objects.select_related("role_record"), pk=user_id)
    is_self = target_user.pk == request.user.pk
    last_active_admin = _is_last_active_admin(target_user)

    source_group = None
    group_param = request.GET.get("group", "").strip()
    if group_param.isdigit():
        source_group = WorkspaceGroup.objects.filter(pk=int(group_param), memberships__user=target_user).first()

    form = AdminUserUpdateForm(request.POST or None, instance=target_user)
    if request.method == "POST" and form.is_valid():
        new_role = form.cleaned_data["role_record"].code
        if is_self and new_role != User.Role.ADMIN:
            form.add_error("role_record", "You cannot remove administrator access from your own account.")
        elif last_active_admin and new_role != User.Role.ADMIN:
            form.add_error("role_record", "At least one active administrator account must remain.")
        else:
            updated = form.save(commit=False)
            updated.is_staff = new_role == User.Role.ADMIN
            updated.save()
            messages.success(request, f"Updated account details for @{updated.username}.")
            redirect_url = reverse("dashboard:admin_user_detail", args=[updated.pk])
            if source_group:
                redirect_url = f"{redirect_url}?group={source_group.pk}"
            return redirect(redirect_url)

    user_projects_qs = (
        target_user.network_projects.annotate(
            requirement_count=Count("requirements", distinct=True),
            allocation_count=Count("requirements__allocation", distinct=True),
            allocated_addresses=Sum("requirements__allocation__allocated_addresses"),
        )
        .order_by("-updated_at")
    )
    user_projects = _decorate_admin_projects(user_projects_qs)
    total_allocated = sum(p.allocated_addresses for p in user_projects)
    user_groups = list(target_user.workspace_groups.order_by("name"))

    return render(
        request,
        "dashboard/admin_user_detail.html",
        {
            **_admin_tab_context("groups" if source_group else "users"),
            "target_user": target_user,
            "source_group": source_group,
            "user_groups": user_groups,
            "form": form,
            "user_projects": user_projects,
            "total_allocated": total_allocated,
            "is_self": is_self,
            "can_deactivate": not is_self and not last_active_admin,
            "can_change_role": not is_self and not last_active_admin,
        },
    )


@role_required(User.Role.ADMIN)
@require_POST
def admin_user_toggle_active(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    if target_user.pk == request.user.pk:
        messages.error(request, "You cannot deactivate your own administrator account.")
        return redirect("dashboard:admin_user_detail", user_id=target_user.pk)
    if target_user.is_active and _is_last_active_admin(target_user):
        messages.error(request, "Cannot deactivate the last active administrator.")
        return redirect("dashboard:admin_user_detail", user_id=target_user.pk)

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=["is_active"])
    state_label = "activated" if target_user.is_active else "deactivated"
    messages.success(request, f"Account @{target_user.username} has been {state_label}.")
    return redirect("dashboard:admin_user_detail", user_id=target_user.pk)


@role_required(User.Role.ADMIN)
@require_POST
def admin_user_change_role(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    if target_user.pk == request.user.pk:
        messages.error(request, "You cannot change your own role.")
        return redirect("dashboard:admin_user_detail", user_id=target_user.pk)
    if target_user.role == User.Role.ADMIN and _is_last_active_admin(target_user):
        messages.error(request, "Cannot demote the last active administrator.")
        return redirect("dashboard:admin_user_detail", user_id=target_user.pk)

    next_role = User.Role.USER if target_user.role == User.Role.ADMIN else User.Role.ADMIN
    target_user.role = next_role
    target_user.is_staff = next_role == User.Role.ADMIN
    target_user.save(update_fields=["role_record", "is_staff"])
    role_label = "Administrator" if next_role == User.Role.ADMIN else "Regular User"
    messages.success(request, f"Changed @{target_user.username} role to {role_label}.")
    return redirect("dashboard:admin_user_detail", user_id=target_user.pk)
