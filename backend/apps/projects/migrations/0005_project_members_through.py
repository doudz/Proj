from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Django does not allow AlterField to add/remove `through=` on a M2M field
    (ValueError: "you cannot alter to or from M2M fields, or add or remove
    through= on M2M fields"). The documented way is to remove and re-add the
    field; the relations themselves are not lost because the previous
    migration (0004) already copied them into ProjectMembership, which is
    what this new `members` field points to."""

    dependencies = [
        ("projects", "0004_migrate_members_to_projectmembership"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="project",
            name="members",
        ),
        migrations.AddField(
            model_name="project",
            name="members",
            field=models.ManyToManyField(
                blank=True,
                related_name="projects",
                through="projects.ProjectMembership",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
