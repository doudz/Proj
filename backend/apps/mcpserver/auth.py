from asgiref.sync import sync_to_async
from django.utils import timezone

from apps.mcpserver.models import ApiToken, hash_token


@sync_to_async
def resolve_bearer_token(raw_token):
    """Look up the user behind a raw API token, or None if it's missing/invalid."""
    if not raw_token:
        return None
    try:
        api_token = ApiToken.objects.select_related("user").get(token_hash=hash_token(raw_token))
    except ApiToken.DoesNotExist:
        return None
    if not api_token.user.is_active:
        return None
    ApiToken.objects.filter(pk=api_token.pk).update(last_used_at=timezone.now())
    return api_token.user
