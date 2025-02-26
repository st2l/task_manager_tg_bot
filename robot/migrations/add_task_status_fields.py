from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('robot', '0006_merge_20250226_1248'),  # Replace with your last migration
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='status',
            field=models.CharField(
                choices=[
                    ('open', 'Open'),
                    ('assigned', 'Assigned'),
                    ('in_progress', 'In Progress'),
                    ('submitted', 'Submitted'),
                    ('completed', 'Completed'),
                    ('overdue', 'Overdue'),
                    ('revision', 'Revision')
                ],
                default='open',
                max_length=20
            ),
        ),
    ]
