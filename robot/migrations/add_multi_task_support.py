from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('robot', '0001_initial'),  # Replace with your last migration
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='is_multi_task',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='TaskAssignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('completed', models.BooleanField(default=False)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('task', models.ForeignKey(on_delete=models.CASCADE, related_name='assignments', to='robot.task')),
                ('user', models.ForeignKey(on_delete=models.CASCADE, to='robot.telegramuser')),
            ],
            options={
                'unique_together': {('task', 'user')},
            },
        ),
        migrations.AddField(
            model_name='task',
            name='assignees',
            field=models.ManyToManyField(related_name='multi_assigned_tasks', through='robot.TaskAssignment', to='robot.TelegramUser'),
        ),
    ]
