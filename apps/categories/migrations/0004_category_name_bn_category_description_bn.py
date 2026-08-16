from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0003_alter_category_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='name_bn',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='category',
            name='description_bn',
            field=models.TextField(blank=True, null=True),
        ),
    ]
