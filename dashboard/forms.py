from django import forms
from django.contrib.auth.forms import UserCreationForm

from accounts.models import Role, User, WorkspaceGroup, normalize_join_code
from accounts.forms import UniqueEmailMixin


class AdminUserFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search users",
        widget=forms.TextInput(attrs={"placeholder": "Username, email, or name"}),
    )
    group = forms.ChoiceField(
        required=False,
        label="Group",
        choices=(),
    )
    role = forms.ChoiceField(
        required=False,
        label="Role",
        choices=(
            ("", "All roles"),
            (User.Role.USER, "Regular User"),
            (User.Role.ADMIN, "Administrator"),
        ),
    )
    status = forms.ChoiceField(
        required=False,
        label="Status",
        choices=(
            ("", "All statuses"),
            ("active", "Active"),
            ("inactive", "Inactive"),
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        group_choices = [("", "All groups"), ("unassigned", "Unassigned")]
        group_choices.extend(
            (str(group.pk), group.name) for group in WorkspaceGroup.objects.order_by("name")
        )
        self.fields["group"].choices = group_choices


class AdminUserUpdateForm(UniqueEmailMixin, forms.ModelForm):
    role_record = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        label="Role",
        empty_label=None,
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "contact_number", "role_record")
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Last name"}),
            "email": forms.EmailInput(attrs={"placeholder": "name@example.com"}),
            "contact_number": forms.TextInput(attrs={"placeholder": "+63 900 000 0000"}),
        }


class AdminUserCreateForm(UniqueEmailMixin, UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "name@example.com"}),
    )
    role_record = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        label="Role",
        initial=User.Role.USER,
        empty_label=None,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name", "contact_number", "role_record")
        widgets = {
            "username": forms.TextInput(attrs={"placeholder": "e.g. jdelacruz"}),
            "first_name": forms.TextInput(attrs={"placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Last name"}),
            "contact_number": forms.TextInput(attrs={"placeholder": "+63 900 000 0000"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = user.role_record_id == User.Role.ADMIN
        if commit:
            user.save()
        return user


class WorkspaceGroupForm(forms.ModelForm):
    class Meta:
        model = WorkspaceGroup
        fields = ("name", "description", "is_joinable")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. CSIT327 Section G01"}),
            "description": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Optional notes about this cohort, lab section, or team"}
            ),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = WorkspaceGroup.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A group with this name already exists.")
        return name


class JoinGroupCodeForm(forms.Form):
    join_code = forms.CharField(
        max_length=16,
        label="Group join code",
        widget=forms.TextInput(
            attrs={
                "placeholder": "XXXX-XXXX",
                "autocomplete": "off",
                "spellcheck": "false",
            }
        ),
    )

    def clean_join_code(self):
        code = normalize_join_code(self.cleaned_data["join_code"])
        if len(code.replace("-", "")) != 8:
            raise forms.ValidationError("Enter a valid 8-character group join code.")
        return code


class AdminGroupAddMemberForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Add member",
        empty_label="Select a user to enroll...",
    )

    def __init__(self, *args, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = User.objects.filter(role_record_id=User.Role.USER, is_active=True).order_by("username")
        if group is not None:
            qs = qs.exclude(group_memberships__group=group)
        self.fields["user"].queryset = qs
        self.fields["user"].label_from_instance = (
            lambda u: f"{u.get_full_name()} (@{u.username})" if u.get_full_name() else f"@{u.username}"
        )
