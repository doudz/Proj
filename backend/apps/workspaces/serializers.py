from django.utils.text import slugify
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.workspaces.models import ExternalContact, Invitation, Membership, Workspace


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "user", "role", "joined_at"]


class WorkspaceSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ["id", "name", "slug", "description", "color", "created_at", "my_role", "members_count"]
        read_only_fields = ["id", "slug", "created_at"]

    def get_my_role(self, obj):
        user = self.context["request"].user
        membership = obj.memberships.filter(user=user).first()
        return membership.role if membership else None

    def get_members_count(self, obj):
        return obj.memberships.count()

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["created_by"] = request.user
        validated_data["slug"] = slugify(validated_data["name"])[:140] or "workspace"
        base_slug = validated_data["slug"]
        i = 1
        while Workspace.objects.filter(slug=validated_data["slug"]).exists():
            i += 1
            validated_data["slug"] = f"{base_slug}-{i}"
        workspace = super().create(validated_data)
        Membership.objects.create(workspace=workspace, user=request.user, role=Membership.Role.OWNER)
        return workspace


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ["id", "email", "role", "token", "created_at", "accepted"]
        read_only_fields = ["id", "token", "created_at", "accepted"]


class ExternalContactSerializer(serializers.ModelSerializer):
    initials = serializers.ReadOnlyField()

    class Meta:
        model = ExternalContact
        fields = ["id", "workspace", "name", "email", "company", "phone", "notes", "color", "initials", "created_at"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)
