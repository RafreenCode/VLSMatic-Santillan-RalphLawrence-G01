from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.models import User
from network_projects.models import NetworkProject, SubnetRequirement
from network_projects.services import allocation_visualization, project_summary

from .decorators import role_required


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
        },
    )


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    recent_qs = NetworkProject.objects.select_related("owner").annotate(
        requirement_count=Count("requirements", distinct=True),
        allocation_count=Count("requirements__allocation", distinct=True),
        allocated_addresses=Sum("requirements__allocation__allocated_addresses"),
    )[:4]
    recent_projects = list(recent_qs)
    for project in recent_projects:
        project.allocated_addresses = project.allocated_addresses or 0
        project.total_addresses = 2 ** (32 - project.prefix_length)
        project.address_consumption = project.allocated_addresses / project.total_addresses * 100
        project.plan_status = "Allocated" if project.allocation_count else "Ready to plan"

    context = {
        "total_users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "total_projects": NetworkProject.objects.count(),
        "total_requirements": SubnetRequirement.objects.count(),
        "total_allocations": SubnetRequirement.objects.filter(allocation__isnull=False).count(),
        "recent_projects": recent_projects,
    }
    return render(request, "dashboard/admin.html", context)
