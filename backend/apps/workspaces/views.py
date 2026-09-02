from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.serializers import UserSerializer
from apps.workspaces.models import ExternalContact, Invitation, Membership, Workspace
from apps.workspaces.permissions import user_workspace_ids
from apps.workspaces.serializers import (
    ExternalContactSerializer,
    InvitationSerializer,
    MembershipSerializer,
    WorkspaceSerializer,
)


class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Workspace.objects.filter(id__in=user_workspace_ids(self.request.user)).distinct()

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        workspace = self.get_object()
        if request.method == "POST":
            # Single-tenant, enterprise deployment: anyone with an account
            # already belongs to the company, so an admin adds them straight
            # from the directory - no e-mail/accept round-trip required (that
            # flow still exists via `invite`, for someone without an account yet).
            my_membership = workspace.memberships.filter(user=request.user).first()
            if not my_membership or my_membership.role not in (Membership.Role.OWNER, Membership.Role.ADMIN):
                return Response({"detail": "Permission refusee."}, status=status.HTTP_403_FORBIDDEN)
            user_id = request.data.get("user_id")
            role = request.data.get("role", Membership.Role.MEMBER)
            if role not in Membership.Role.values:
                return Response({"detail": "Role invalide."}, status=status.HTTP_400_BAD_REQUEST)
            if role == Membership.Role.OWNER:
                return Response(
                    {"detail": "Le role proprietaire ne peut pas etre attribue ici."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            membership, _ = Membership.objects.update_or_create(
                workspace=workspace, user_id=user_id, defaults={"role": role}
            )
            return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)
        memberships = workspace.memberships.select_related("user")
        return Response(MembershipSerializer(memberships, many=True).data)

    @action(detail=True, methods=["post"], url_path="invite")
    def invite(self, request, pk=None):
        workspace = self.get_object()
        membership = workspace.memberships.get(user=request.user)
        if membership.role not in (Membership.Role.OWNER, Membership.Role.ADMIN):
            return Response({"detail": "Permission refusee."}, status=status.HTTP_403_FORBIDDEN)
        serializer = InvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(workspace=workspace, invited_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="accept-invite/(?P<token>[^/.]+)")
    def accept_invite(self, request, pk=None, token=None):
        invitation = get_object_or_404(Invitation, token=token, workspace_id=pk)
        Membership.objects.get_or_create(
            workspace=invitation.workspace, user=request.user, defaults={"role": invitation.role}
        )
        invitation.accepted = True
        invitation.save(update_fields=["accepted"])
        return Response(WorkspaceSerializer(invitation.workspace, context={"request": request}).data)

    @action(detail=True, methods=["delete"], url_path="members/(?P<user_id>[^/.]+)")
    def remove_member(self, request, pk=None, user_id=None):
        workspace = self.get_object()
        my_membership = workspace.memberships.get(user=request.user)
        if my_membership.role not in (Membership.Role.OWNER, Membership.Role.ADMIN):
            return Response({"detail": "Permission refusee."}, status=status.HTTP_403_FORBIDDEN)
        workspace.memberships.filter(user_id=user_id).exclude(role=Membership.Role.OWNER).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExternalContactViewSet(viewsets.ModelViewSet):
    """Non-user people/subcontractors that tasks can be assigned to (outsourced work).
    They are notified by e-mail only, since they never log into the app."""

    serializer_class = ExternalContactSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["workspace"]
    search_fields = ["name", "email", "company"]

    def get_queryset(self):
        return ExternalContact.objects.filter(workspace_id__in=user_workspace_ids(self.request.user))
