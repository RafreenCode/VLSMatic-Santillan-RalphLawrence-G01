from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.models import User
from network_projects.models import NetworkProject, SubnetRequirement

from .decorators import role_required


@login_required
def dashboard(request):
    if request.user.role == User.Role.ADMIN:
        return redirect("dashboard:admin")
    return redirect("dashboard:user")


@role_required(User.Role.USER)
def user_dashboard(request):
    projects = request.user.network_projects.all()
    return render(
        request,
        "dashboard/user.html",
        {"project_count": projects.count(), "recent_projects": projects[:3]},
    )


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    context = {
        "total_users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "total_projects": NetworkProject.objects.count(),
        "total_requirements": SubnetRequirement.objects.count(),
        "recent_projects": NetworkProject.objects.select_related("owner")[:4],
    }
    return render(request, "dashboard/admin.html", context)
