from django.contrib import admin
from .models import Profile, Post, Follow, FollowRequest, Like, Comment, Notification, Message, Conversation


# ─────────────────────────────────────────────
#  PROFILE
# ─────────────────────────────────────────────

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display   = ('user', 'private_account', 'website')
    search_fields  = ('user__username', 'user__email', 'bio')
    list_filter    = ('private_account',)
    raw_id_fields  = ('user',)


# ─────────────────────────────────────────────
#  POST
# ─────────────────────────────────────────────

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display   = ('id', 'user', 'location', 'created_at')
    search_fields  = ('user__username', 'caption', 'location')
    list_filter    = ('created_at',)
    raw_id_fields  = ('user',)
    ordering       = ('-created_at',)


# ─────────────────────────────────────────────
#  FOLLOW
# ─────────────────────────────────────────────

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display   = ('follower', 'following', 'created_at')
    search_fields  = ('follower__username', 'following__username')
    raw_id_fields  = ('follower', 'following')


# ─────────────────────────────────────────────
#  FOLLOW REQUEST
# ─────────────────────────────────────────────

@admin.register(FollowRequest)
class FollowRequestAdmin(admin.ModelAdmin):
    list_display   = ('sender', 'receiver', 'created_at')
    search_fields  = ('sender__username', 'receiver__username')
    raw_id_fields  = ('sender', 'receiver')


# ─────────────────────────────────────────────
#  LIKE
# ─────────────────────────────────────────────

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display   = ('user', 'post', 'created_at')
    search_fields  = ('user__username',)
    raw_id_fields  = ('user', 'post')


# ─────────────────────────────────────────────
#  COMMENT
# ─────────────────────────────────────────────

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display   = ('user', 'post', 'text', 'created_at')
    search_fields  = ('user__username', 'text')
    raw_id_fields  = ('user', 'post')


# ─────────────────────────────────────────────
#  NOTIFICATION
# ─────────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display   = ('sender', 'receiver', 'notif_type', 'is_read', 'created_at')
    search_fields  = ('sender__username', 'receiver__username')
    list_filter    = ('notif_type', 'is_read')
    raw_id_fields  = ('sender', 'receiver', 'post')


# ─────────────────────────────────────────────
#  CONVERSATION
# ─────────────────────────────────────────────

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display  = ('id', 'created_at', 'updated_at')
    filter_horizontal = ('participants',)


# ─────────────────────────────────────────────
#  MESSAGE
# ─────────────────────────────────────────────

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display   = ('sender', 'receiver', 'text', 'is_read', 'created_at')
    search_fields  = ('sender__username', 'receiver__username', 'text')
    list_filter    = ('is_read', 'created_at')
    raw_id_fields  = ('sender', 'receiver', 'conversation')