from django.db import migrations

def seed_platform_direct_category(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    Category.objects.get_or_create(
        name="Platform Direct (Admin)",
        slug="platform-direct-admin",
        description="Default category for direct platform uploads and admin listings."
    )

def remove_platform_direct_category(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    Category.objects.filter(slug="platform-direct-admin").delete()

class Migration(migrations.Migration):
    dependencies = [
        ("categories", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_platform_direct_category, remove_platform_direct_category),
    ]
