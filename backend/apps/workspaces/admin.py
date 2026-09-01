from django.contrib import admin

from apps.workspaces.models import Invitation, Membership, Workspace


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_by", "created_at"]
    search_fields = ["name", "slug"]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["workspace", "user", "role", "joined_at"]
    list_filter = ["role"]


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ["workspace", "email", "role", "accepted", "created_at"]
