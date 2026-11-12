from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .forms import ProfileForm, RegistrationForm


class VLSMaticLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_invalid(self, form):
        messages.error(self.request, "We could not sign you in. Check your username and password.")
        return super().form_invalid(form)


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    return redirect("accounts:register")


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your account is ready. Sign in to continue.")
        return redirect("accounts:login")

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    form = ProfileForm(request.POST if request.method == "POST" else None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile details were updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})
