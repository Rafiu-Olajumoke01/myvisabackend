from django.db import migrations
import random

def fix_and_apply(apps, schema_editor):
    # Step 1: backfill empty service_ids
    schema_editor.execute("""
        UPDATE packages_package
        SET service_id = floor(random() * 9000 + 1000)::text
        WHERE service_id = '' OR service_id IS NULL;
    """)
    # Step 2: add unique constraint only if it doesn't exist
    schema_editor.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'packages_package_service_id_key'
            ) THEN
                ALTER TABLE packages_package ADD CONSTRAINT packages_package_service_id_key UNIQUE (service_id);
            END IF;
        END
        $$;
    """)

class Migration(migrations.Migration):
    dependencies = [
        ('packages', '0006_package_service_id'),
    ]
    operations = [
        migrations.RunPython(fix_and_apply, migrations.RunPython.noop),
    ]