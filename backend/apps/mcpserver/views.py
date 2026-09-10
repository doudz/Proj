from rest_framework import mixins, permissions, viewsets
from rest_framework.response import Response

from apps.mcpserver.models import ApiToken
from apps.mcpserver.serializers import ApiTokenSerializer


class ApiTokenViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Personal access tokens used to connect an MCP client (AI assistant) to
    this account. No update endpoint on purpose: a token is either kept
    as-is or revoked (deleted) and a new one issued."""

    serializer_class = ApiTokenSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ApiToken.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        name = (request.data.get("name") or "Jeton API").strip()[:100]
        instance, raw_token = ApiToken.issue(request.user, name)
        data = ApiTokenSerializer(instance).data
        data["token"] = raw_token
        return Response(data, status=201)
