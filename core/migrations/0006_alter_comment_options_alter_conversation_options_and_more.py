# Migration 0006 — rewritten to match actual DB state.
#
# The original auto-generated 0006 included a RenameIndex operation for
# 'followreq_sender_idx' → 'core_follow_sender__e38239_idx', but that old name
# never existed in the DB (it was always the Django-generated name
# 'core_followrequest_sender_id_1927c9d2').  Removing that broken op.
#
# This migration:
#   1. Updates verbose_name_plural / ordering Meta options on all models (no-op SQL).
#   2. Removes the four old auto-generated named indexes that 0004 created.
#   3. Adds the new, canonically-named indexes that models.py now declares.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_fix_message_conversation'),
    ]

    operations = [
        # ── Meta-only changes (no SQL) ──────────────────────────────────────
        migrations.AlterModelOptions(
            name='comment',
            options={'ordering': ['created_at'], 'verbose_name_plural': 'Comments'},
        ),
        migrations.AlterModelOptions(
            name='conversation',
            options={'ordering': ['-updated_at'], 'verbose_name_plural': 'Conversations'},
        ),
        migrations.AlterModelOptions(
            name='follow',
            options={'verbose_name_plural': 'Follows'},
        ),
        migrations.AlterModelOptions(
            name='followrequest',
            options={'verbose_name_plural': 'Follow Requests'},
        ),
        migrations.AlterModelOptions(
            name='like',
            options={'verbose_name_plural': 'Likes'},
        ),
        migrations.AlterModelOptions(
            name='message',
            options={'ordering': ['created_at'], 'verbose_name_plural': 'Messages'},
        ),
        migrations.AlterModelOptions(
            name='notification',
            options={'ordering': ['-created_at'], 'verbose_name_plural': 'Notifications'},
        ),
        migrations.AlterModelOptions(
            name='post',
            options={'ordering': ['-created_at'], 'verbose_name_plural': 'Posts'},
        ),
        migrations.AlterModelOptions(
            name='profile',
            options={'verbose_name': 'Profile', 'verbose_name_plural': 'Profiles'},
        ),

        # ── Remove old indexes from migration 0004 ──────────────────────────
        # (These exist in the DB; safe to remove.)
        migrations.RemoveIndex(
            model_name='comment',
            name='core_commen_post_id_6aa857_idx',
        ),
        migrations.RemoveIndex(
            model_name='like',
            name='core_like_post_id_777ee2_idx',
        ),
        migrations.RemoveIndex(
            model_name='message',
            name='core_messag_sender__2a6008_idx',
        ),
        migrations.RemoveIndex(
            model_name='message',
            name='core_messag_convers_d2b392_idx',
        ),

        # ── Add new canonical indexes matching models.py ─────────────────────

        # Comment: compound (post, created_at) for paginated comment lists
        migrations.AddIndex(
            model_name='comment',
            index=models.Index(fields=['post', 'created_at'], name='comment_post_time_idx'),
        ),

        # Like: compound (post, user) covers uniqueness check + like counts
        migrations.AddIndex(
            model_name='like',
            index=models.Index(fields=['post', 'user'], name='like_post_user_idx'),
        ),
        migrations.AddIndex(
            model_name='like',
            index=models.Index(fields=['user'], name='like_user_idx'),
        ),

        # Message: compound (conversation, created_at) for conversation thread queries
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['conversation', 'created_at'], name='message_conv_time_idx'),
        ),
        # Message: (sender, receiver) for legacy DM lookups still in DB
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['sender', 'receiver'], name='message_sender_receiver_idx'),
        ),

        # FollowRequest: named sender index (was unnamed / auto-named before)
        migrations.AddIndex(
            model_name='followrequest',
            index=models.Index(fields=['sender'], name='followreq_sender_named_idx'),
        ),

        # Post: standalone created_at index for global explore/trending queries
        migrations.AddIndex(
            model_name='post',
            index=models.Index(fields=['-created_at'], name='post_created_at_idx'),
        ),

        # Conversation: updated_at for inbox sort
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(fields=['-updated_at'], name='conversation_updated_idx'),
        ),
    ]
