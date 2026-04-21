from django.db import migrations

def fix_migration_state(apps, schema_editor):
    schema_editor.execute(
        "DELETE FROM django_migrations WHERE app = 'packages' AND name = '0007_alter_package_service_id';"
    )

class Migration(migrations.Migration):

    dependencies = [
        ('packages', '0006_5_backfill_service_id'),
    ]

    operations = [
        migrations.RunPython(fix_migration_state, migrations.RunPython.noop),
    ]
