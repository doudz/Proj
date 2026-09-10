import hashlib
import secrets

from django.conf import settings
from django.db import models

TOKEN_PREFIX = "gf_"


def _generate_raw_token():
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(raw_token):
    return hashlib.sha256(raw_token.encode()).hexdigest()


class ApiToken(models.Model):
    """A personal access token letting an external client - typically an AI
    assistant connected through the MCP connector - act as this user via the
    API. Only a salted hash is stored; the raw token is generated once,
    returned to the caller at creation time and never retrievable again
    (same guarantee as e.g. GitHub personal access tokens)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_tokens")
    name = models.CharField(max_length=100)
    token_hash = models.CharField(max_length=64, unique=True)
    display_prefix = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.user})"

    @classmethod
    def issue(cls, user, name):
        """Create a token and return (instance, raw_token) - raw_token is shown once."""
        raw_token = _generate_raw_token()
        instance = cls.objects.create(
            user=user,
            name=name,
            token_hash=hash_token(raw_token),
            display_prefix=raw_token[: len(TOKEN_PREFIX) + 8],
        )
        return instance, raw_token
