from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .forms import ProfileForm, RegistrationForm
from .profile_photos import ProfilePhotoStorageError, delete_profile_photo, upload_profile_photo


class VLSMaticLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_invalid(self, form):
        messages.error(self.request, "We could not sign you in. Check your username and password.")
        return super().form_invalid(form)


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    return redirect("accounts:login")


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
    form = ProfileForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        instance=request.user,
    )
    if request.method == "POST" and form.is_valid():
        old_photo_path = request.user.profile_photo_path
        uploaded_photo = form.cleaned_data.get("profile_photo")
        remove_photo = form.cleaned_data.get("remove_profile_photo")
        new_photo_path = ""
        try:
            if uploaded_photo:
                new_photo_path = upload_profile_photo(request.user.pk, uploaded_photo)
            user = form.save(commit=False)
            if new_photo_path:
                user.profile_photo_path = new_photo_path
            elif remove_photo:
                user.profile_photo_path = ""
            user.save()
        except ProfilePhotoStorageError as exc:
            form.add_error("profile_photo", str(exc))
        else:
            if old_photo_path and (new_photo_path or remove_photo):
                try:
                    delete_profile_photo(old_photo_path)
                except ProfilePhotoStorageError:
                    messages.warning(request, "Your profile was updated, but the previous photo could not be cleaned up.")
            messages.success(request, "Your profile details were updated.")
            return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})
