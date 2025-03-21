# Generated by Django 4.2.9 on 2024-09-12 05:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0015_settings_last_outgoing_message_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='settings',
            old_name='last_outgoing_message',
            new_name='last_reminder_id',
        ),
        migrations.RemoveField(
            model_name='settings',
            name='last_outgoing_message_time',
        ),
        migrations.AddField(
            model_name='settings',
            name='last_reminder_time',
            field=models.TextField(default=None, null=True),
        ),
    ]
