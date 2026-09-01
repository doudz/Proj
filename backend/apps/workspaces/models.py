import uuid

from django.conf import settings
from django.db import models


class Workspace(models.Model):
    """Top level container grouping projects and members - an organization or team account."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#1976D2")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="workspaces_created")
    created_at = models.DateTimeField(auto_now_add=True)

    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Membership", related_name="workspaces")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Proprietaire"
        ADMIN = "admin", "Administrateur"
        MEMBER = "member", "Membre"
        GUEST = "guest", "Invite"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("workspace", "user")

    def __str__(self):
        return f"{self.user} @ {self.workspace} ({self.role})"


class Invitation(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    role = models.CharField(max_length=10, choices=Membership.Role.choices, default=Membership.Role.MEMBER)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)

    class Meta:
        unique_together = ("workspace", "email")


class ExternalContact(models.Model):
    """A person or subcontractor who can be assigned tasks without holding a
    GanttFlow account - typically used to track outsourced/external work.
    Notified by e-mail only, since they never log into the app."""

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="external_contacts")
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    company = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#8D6E63")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.company})" if self.company else self.name

    @property
    def initials(self):
        parts = self.name.split()
        letters = "".join(p[0] for p in parts[:2] if p)
        return letters.upper() or "EX"
