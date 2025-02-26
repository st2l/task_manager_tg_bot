from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('robot', 'add_multi_task_support'),  # Replace with your last migration
    ]

    operations = [
        migrations.AddField(
            model_name='taskassignment',
            name='accepted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='taskassignment',
            name='accepted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
