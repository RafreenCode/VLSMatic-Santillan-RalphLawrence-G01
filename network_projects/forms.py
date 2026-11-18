from ipaddress import IPv4Network, AddressValueError, NetmaskValueError

from django import forms
from django.core.exceptions import ValidationError

from .models import NetworkProject, SubnetRequirement


class NetworkProjectForm(forms.ModelForm):
    base_network = forms.CharField(
        label="Base IPv4 network",
        help_text="Enter the network address, for example 192.168.10.0.",
        widget=forms.TextInput(attrs={"placeholder": "192.168.10.0", "inputmode": "decimal"}),
    )
    prefix_length = forms.IntegerField(
        label="Prefix length",
        min_value=8,
        max_value=30,
        help_text="Use a prefix from /8 through /30.",
        widget=forms.NumberInput(attrs={"placeholder": "24"}),
    )

    class Meta:
        model = NetworkProject
        fields = ("name", "description", "base_network", "prefix_length")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Campus laboratory"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Optional planning notes"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise ValidationError("Enter a project name.")
        return name

    def clean(self):
        cleaned = super().clean()
        address = cleaned.get("base_network")
        prefix = cleaned.get("prefix_length")
        if address and prefix is not None:
            try:
                network = IPv4Network(f"{address}/{prefix}", strict=True)
            except (AddressValueError, NetmaskValueError, ValueError):
                self.add_error(
                    "base_network",
                    "Enter the network address for this prefix. Host addresses are not accepted.",
                )
            else:
                cleaned["base_network"] = str(network.network_address)
        return cleaned


class SubnetRequirementForm(forms.ModelForm):
    class Meta:
        model = SubnetRequirement
        fields = ("name", "required_hosts")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Computer laboratory"}),
            "required_hosts": forms.NumberInput(attrs={"min": 1, "placeholder": "50"}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project or getattr(self.instance, "project", None)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise ValidationError("Enter a subnet name.")
        if self.project:
            matches = self.project.requirements.filter(name__iexact=name)
            if self.instance.pk:
                matches = matches.exclude(pk=self.instance.pk)
            if matches.exists():
                raise ValidationError("This project already has a subnet with that name.")
        return name

    def clean_required_hosts(self):
        hosts = self.cleaned_data["required_hosts"]
        if hosts < 1:
            raise ValidationError("Required hosts must be at least 1.")
        if self.project:
            total_addresses = 2 ** (32 - self.project.prefix_length)
            if hosts + 2 > total_addresses:
                raise ValidationError("This requirement cannot fit inside the project's base network.")
        return hosts

