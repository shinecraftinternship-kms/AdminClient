from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("scanner_api", "0008_asset_assigned_to"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                help_text="Admin user who owns this client",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="owned_clients",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
