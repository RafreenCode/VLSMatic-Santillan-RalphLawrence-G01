from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import redirect, render

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
    recent_projects = list(projects[:4])
    for project in recent_projects:
        project.allocated_addresses = project.allocated_addresses or 0
        project.total_addresses = 2 ** (32 - project.prefix_length)
        project.address_consumption = project.allocated_addresses / project.total_addresses * 100
    resume_project = next((project for project in recent_projects if project.allocation_count), recent_projects[0] if recent_projects else None)
    resume_requirements = []
    resume_summary = None
    resume_visualization = []
    if resume_project:
        resume_requirements = list(resume_project.requirements.select_related("allocation"))
        resume_summary = project_summary(resume_project, resume_requirements)
        resume_visualization = allocation_visualization(resume_project, resume_requirements)
    return render(
        request,
        "dashboard/user.html",
        {
            "project_count": projects.count(),
            "subnet_count": request.user.network_projects.aggregate(total=Count("requirements"))["total"],
            "active_plan_count": projects.filter(calculation_run__isnull=False).count(),
            "allocated_address_count": projects.aggregate(total=Sum("requirements__allocation__allocated_addresses"))["total"] or 0,
            "recent_projects": recent_projects,
            "resume_project": resume_project,
            "resume_summary": resume_summary,
            "resume_visualization": resume_visualization,
        },
    )


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    context = {
        "total_users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "total_projects": NetworkProject.objects.count(),
        "total_requirements": SubnetRequirement.objects.count(),
        "total_allocations": SubnetRequirement.objects.filter(allocation__isnull=False).count(),
        "recent_projects": NetworkProject.objects.select_related("owner")[:4],
    }
    return render(request, "dashboard/admin.html", context)
