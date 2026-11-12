from io import BytesIO

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name")
        widgets = {
            "username": forms.TextInput(attrs={"autocomplete": "username"}),
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = User.Role.USER
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    profile_photo = forms.ImageField(
        required=False,
        label="Profile photo",
        help_text="JPEG, PNG, or WebP. Maximum 5 MB.",
        widget=forms.ClearableFileInput(
            attrs={"accept": "image/jpeg,image/png,image/webp", "data-profile-photo-input": ""}
        ),
    )
    remove_profile_photo = forms.BooleanField(required=False, label="Remove current photo")

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "contact_number")
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "contact_number": forms.TextInput(attrs={"autocomplete": "tel"}),
        }

    def clean_profile_photo(self):
        photo = self.cleaned_data.get("profile_photo")
        if not photo:
            return photo
        if photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Choose an image smaller than 5 MB.")
        try:
            image = Image.open(photo)
            width, height = image.size
            image.verify()
            image_format = image.format
        except (UnidentifiedImageError, OSError, ValueError):
            raise forms.ValidationError("Choose a valid JPEG, PNG, or WebP image.")
        finally:
            photo.seek(0)
        if image_format not in {"JPEG", "PNG", "WEBP"}:
            raise forms.ValidationError("Choose a JPEG, PNG, or WebP image.")
        if width > 4096 or height > 4096:
            raise forms.ValidationError("Choose an image no larger than 4096 by 4096 pixels.")
        photo.seek(0)
        with Image.open(photo) as source:
            source = ImageOps.exif_transpose(source)
            resized = ImageOps.fit(source, (512, 512), method=Image.Resampling.LANCZOS)
            if resized.mode in {"RGBA", "LA"}:
                background = Image.new("RGB", resized.size, "white")
                background.paste(resized, mask=resized.getchannel("A"))
                resized = background
            else:
                resized = resized.convert("RGB")
            output = BytesIO()
            resized.save(output, format="WEBP", quality=85, method=6)

        optimized = SimpleUploadedFile("profile.webp", output.getvalue(), content_type="image/webp")
        optimized.image_format = "WEBP"
        return optimized

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email
