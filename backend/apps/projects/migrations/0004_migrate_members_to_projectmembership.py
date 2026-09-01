from django.db import migrations


def copy_members_forward(apps, schema_editor):
    """Every existing Project.members row becomes a ProjectMembership with the
    'admin' role, preserving the full access these members already had before
    per-project roles existed."""
    Project = apps.get_model("projects", "Project")
    ProjectMembership = apps.get_model("projects", "ProjectMembership")
    memberships = [
        ProjectMembership(project=project, user=user, role="admin")
        for project in Project.objects.prefetch_related("members").all()
        for user in project.members.all()
    ]
    ProjectMembership.objects.bulk_create(memberships, ignore_conflicts=True)


def copy_members_backward(apps, schema_editor):
    ProjectMembership = apps.get_model("projects", "ProjectMembership")
    ProjectMembership.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0003_projectmembership"),
    ]

    operations = [
        migrations.RunPython(copy_members_forward, copy_members_backward),
    ]
