from django_auth_ldap.backend import LDAPBackend


class EmailLDAPBackend(LDAPBackend):
    """Bridges django-auth-ldap to this project's email-based login.

    django_auth_ldap.backend.LDAPBackend only looks at the "username" kwarg,
    but EmailTokenObtainPairSerializer (USERNAME_FIELD = "email") always
    calls authenticate(email=..., password=..., request=...). Forward the
    email straight through as the username django-auth-ldap expects.
    """

    def authenticate(self, request, email=None, password=None, **kwargs):
        if email is None or password is None:
            return None
        return super().authenticate(request, username=email, password=password, **kwargs)
