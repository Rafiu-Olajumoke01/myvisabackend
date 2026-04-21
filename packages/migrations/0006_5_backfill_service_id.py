from django.db import migrations
import random

def backfill_service_ids(apps, schema_editor):
    Package = apps.get_model('packages', 'Package')
    used = set(Package.objects.exclude(service_id='').values_list('service_id', flat=True))
    for pkg in Package.objects.filter(service_id=''):
        while True:
            new_id = str(random.randint(1000, 9999))
            if new_id not in used:
                pkg.service_id = new_id
                pkg.save(update_fields=['service_id'])
                used.add(new_id)
                break

class Migration(migrations.Migration):
    dependencies = [
        ('packages', '0006_package_service_id'),
    ]
    operations = [
        migrations.RunPython(backfill_service_ids, migrations.RunPython.noop),
    ]