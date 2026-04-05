# Migration 0007 — Make Message.conversation non-nullable.
#
# Migration 0005 backfilled all orphan Messages with a Conversation.
# This migration removes null=True from the conversation FK so the DB
# enforces the constraint going forward.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_alter_comment_options_alter_conversation_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='conversation',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='messages',
                to='core.conversation',
            ),
        ),
    ]
