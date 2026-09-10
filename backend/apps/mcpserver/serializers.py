from rest_framework import serializers

from apps.mcpserver.models import ApiToken


class ApiTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiToken
        fields = ["id", "name", "display_prefix", "created_at", "last_used_at"]
        read_only_fields = fields
