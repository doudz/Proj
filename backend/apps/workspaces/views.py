from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.serializers import UserSerializer
from apps.workspaces.models import Invitation, Membership, Workspace
from apps.workspaces.permissions import user_workspace_ids
from apps.workspaces.serializers import InvitationSerializer, MembershipSerializer, WorkspaceSerializer


class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Workspace.objects.filter(id__in=user_workspace_ids(self.request.user)).distinct()

    @action(detail=True, methods=["get"], url_path="members")
    def members(self, request, pk=None):
        workspace = self.get_object()
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
