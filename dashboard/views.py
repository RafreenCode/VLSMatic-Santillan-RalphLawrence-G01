from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.models import User

from .decorators import role_required


@login_required
def dashboard(request):
    if request.user.role == User.Role.ADMIN:
        return redirect("dashboard:admin")
    return redirect("dashboard:user")


@role_required(User.Role.USER)
def user_dashboard(request):
    return render(request, "dashboard/user.html")


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    context = {
        "total_users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
    }
    return render(request, "dashboard/admin.html", context)
