from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class SchoolIdOrEmailBackend(ModelBackend):
    """Lets people log in with their School ID *or* their email address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        User = get_user_model()
        ident = username.strip()
        user = User.objects.filter(
            Q(school_id__iexact=ident) | Q(email__iexact=ident) | Q(username__iexact=ident)
        ).first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
