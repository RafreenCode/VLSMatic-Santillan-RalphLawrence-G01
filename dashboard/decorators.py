from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction

from accounts.models import Role, User


def role_required(*roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def serialize_admin_changes(view_func):
    """Serialize role changes and recheck the acting administrator after the lock."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.method != "POST":
            return view_func(request, *args, **kwargs)
        with transaction.atomic():
            Role.objects.select_for_update().get(pk=User.Role.ADMIN)
            if not User.objects.filter(pk=request.user.pk, role_record_id=User.Role.ADMIN, is_active=True).exists():
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
    return wrapped
