"""
Migration 0005: Backfill Conversation for orphan Messages.

Assigns a Conversation to every Message that has conversation=None.
For each (sender, receiver) pair it finds-or-creates a Conversation and
links the message to it.

New performance indexes are handled by migration 0006 (auto-generated).
"""

from django.db import migrations


def backfill_conversations(apps, schema_editor):
    """
    For every Message with conversation=None, find or create a Conversation
    for the (sender, receiver) pair and link the message to it.
    """
    Message      = apps.get_model('core', 'Message')
    Conversation = apps.get_model('core', 'Conversation')

    orphan_msgs = Message.objects.filter(conversation__isnull=True).select_related('sender', 'receiver')

    # Build a (min_id, max_id) -> Conversation map to avoid creating duplicates
    pair_to_conv = {}

    for msg in orphan_msgs:
        # Canonical key: always (smaller_id, larger_id)
        key = (min(msg.sender_id, msg.receiver_id), max(msg.sender_id, msg.receiver_id))

        if key not in pair_to_conv:
            # Find an existing conversation that has BOTH users as participants
            existing = (
                Conversation.objects
                .filter(participants=msg.sender)
                .filter(participants=msg.receiver)
                .first()
            )
            if existing:
                pair_to_conv[key] = existing
            else:
                conv = Conversation.objects.create()
                conv.participants.add(msg.sender, msg.receiver)
                pair_to_conv[key] = conv

        msg.conversation = pair_to_conv[key]
        msg.save(update_fields=['conversation'])


def reverse_backfill(apps, schema_editor):
    """Reverse: this is a data-only migration; nothing structural to undo."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_conversation_alter_comment_options_and_more'),
    ]

    operations = [
        # Data migration only — assign Conversation to every orphan Message
        migrations.RunPython(backfill_conversations, reverse_code=reverse_backfill),
    ]
