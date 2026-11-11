from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .decorators import role_required
from .forms import ProfileForm, RegistrationForm
from .models import User


class VLSMaticLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_invalid(self, form):
        messages.error(self.request, "We could not sign you in. Check your username and password.")
        return super().form_invalid(form)


def home(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    return redirect("accounts:register")


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your account is ready. Sign in to continue.")
        return redirect("accounts:login")

    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard(request):
    if request.user.role == User.Role.ADMIN:
        return redirect("accounts:admin_dashboard")
    return redirect("accounts:user_dashboard")


@role_required(User.Role.USER)
def user_dashboard(request):
    return render(request, "accounts/user_dashboard.html")


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    context = {
        "total_users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
    }
    return render(request, "accounts/admin_dashboard.html", context)


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile details were updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})
