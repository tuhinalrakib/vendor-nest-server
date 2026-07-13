from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_product_approval_status_product_description_bn_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='digital_file',
            field=models.FileField(blank=True, max_length=500, null=True, upload_to='digital_products/'),
        ),
        migrations.AlterField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, max_length=500, null=True, upload_to='products/'),
        ),
    ]
