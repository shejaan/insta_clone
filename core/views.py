from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse

from .models import Post, Like, Comment, Follow, FollowRequest, Notification, Message


# =========================
# AUTH
# =========================

def register_view(request):

    if request.method == "POST":

        email    = request.POST.get("email", "").strip()
        fullname = request.POST.get("fullname", "").strip()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        is_ajax  = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        def err(msg, field=None):
            if is_ajax:
                return JsonResponse({"success": False, "error": msg, "field": field})
            messages.error(request, msg)
            return redirect("register")

        # ── Empty field checks ──
        if not email:
            return err("Please enter your mobile number or email.", "email")
        if not fullname:
            return err("Please enter your full name.", "fullname")
        if not username:
            return err("Please enter a username.", "username")
        if not password:
            return err("Please enter a password.", "password")

        # ── Password length ──
        if len(password) < 6:
            return err("Password must be at least 6 characters.", "password")

        # ── Username format ──
        import re
        if not re.match(r'^[a-z0-9._]{3,30}$', username):
            return err("Username must be 3–30 characters: only letters, numbers, . or _", "username")

        # ── Username uniqueness ──
        if User.objects.filter(username=username).exists():
            return err("That username is already taken. Try another one.", "username")

        # ── Email uniqueness ──
        if User.objects.filter(email=email).exists():
            return err("An account with that email already exists.", "email")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        user.first_name = fullname
        user.save()
        login(request, user)

        if is_ajax:
            return JsonResponse({"success": True, "redirect": reverse("home")})

        messages.success(request, f"Welcome to Instagram, @{username}! 🎉 Your account is ready.")
        return redirect("home")

    return render(request, "signup.html")




def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        is_ajax  = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        # ── Basic empty-field checks ──
        if not username and not password:
            error = "Please enter your username and password."
        elif not username:
            error = "Please enter your username or email."
        elif not password:
            error = "Please enter your password."
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if is_ajax:
                    return JsonResponse({"success": True, "redirect": reverse("home")})
                return redirect("home")
            else:
                error = "Sorry, your password was incorrect. Please double-check your password."

        # ── Error path ──
        if is_ajax:
            return JsonResponse({"success": False, "error": error})
        messages.error(request, error)
        return redirect("login")

    return render(request, "login.html")

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('login')


# =========================
# CHECK AVAILABILITY (AJAX)
# =========================

def check_availability(request):
    """
    GET /check-availability/?type=username&value=john
    GET /check-availability/?type=email&value=john@gmail.com
    Returns: {"available": true/false}
    """
    check_type = request.GET.get("type", "")
    value      = request.GET.get("value", "").strip()

    if not value:
        return JsonResponse({"available": True})

    if check_type == "username":
        exists = User.objects.filter(username__iexact=value).exists()
    elif check_type == "email":
        exists = User.objects.filter(email__iexact=value).exists()
    else:
        return JsonResponse({"error": "Invalid type"}, status=400)

    return JsonResponse({"available": not exists})



# =========================
# HOME FEED
# =========================

@login_required
def home_view(request):

    posts = Post.objects.all().order_by('-created_at')

    follow_requests = FollowRequest.objects.filter(receiver=request.user)

    notifications = Notification.objects.filter(
        receiver=request.user
    ).order_by('-created_at')

    unread_notifications_count = notifications.filter(
        is_read=False
    ).count()

    # IDs of users the current user already follows
    following_ids = Follow.objects.filter(
        follower=request.user
    ).values_list('following_id', flat=True)

    # IDs of users the current user has sent a pending follow request to
    sent_request_ids = FollowRequest.objects.filter(
        sender=request.user
    ).values_list('receiver_id', flat=True)

    # Suggested = exclude yourself + already following + pending requests
    # NOTE: We do NOT exclude follower_ids so that people who follow you
    # appear as suggestions (giving you a chance to follow back).
    suggested_users = User.objects.exclude(
        id=request.user.id
    ).exclude(
        id__in=following_ids
    ).exclude(
        id__in=sent_request_ids
    )[:5]

    context = {
        "posts": posts,
        "follow_requests": follow_requests,
        "notifications": notifications,
        "unread_notifications_count": unread_notifications_count,
        "suggested_users": suggested_users,
        "following_ids": list(following_ids),
        "sent_request_ids": list(sent_request_ids),
        "follower_ids": list(Follow.objects.filter(following=request.user).values_list('follower_id', flat=True)),
    }

    return render(request, "homepage.html", context)


# =========================
# PROFILE
# =========================

@login_required
def profile_view(request, username):

    profile_user = get_object_or_404(User, username=username)

    posts = Post.objects.filter(user=profile_user).order_by('-created_at')

    # Followers: people who follow profile_user
    followers = Follow.objects.filter(following=profile_user).select_related('follower')
    followers_list = [f.follower for f in followers]

    # Following: people profile_user follows
    following = Follow.objects.filter(follower=profile_user).select_related('following')
    following_list = [f.following for f in following]

    # Is the logged-in user following this profile?
    is_following = Follow.objects.filter(
        follower=request.user,
        following=profile_user
    ).exists()

    # Has the logged-in user sent a pending follow request?
    has_sent_request = FollowRequest.objects.filter(
        sender=request.user,
        receiver=profile_user
    ).exists()

    context = {
        "profile_user": profile_user,
        "posts": posts,
        "followers_list": followers_list,
        "following_list": following_list,
        "followers_count": len(followers_list),
        "following_count": len(following_list),
        "is_following": is_following,
        "has_sent_request": has_sent_request,
    }

    return render(request, "profile.html", context)



# =========================
# CREATE POST
# =========================

@login_required
def create_post(request):

    if request.method == "POST":

        image    = request.FILES.get("image")
        caption  = request.POST.get("caption", "").strip()
        location = request.POST.get("location", "").strip()
        is_ajax  = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        if not image:
            if is_ajax:
                return JsonResponse({"success": False, "error": "Please select an image."})
            messages.error(request, "Please select an image.")
            return redirect("home")

        post = Post.objects.create(
            user=request.user,
            image=image,
            caption=caption,
            location=location
        )

        if is_ajax:
            return JsonResponse({
                "success": True,
                "message": "Post shared successfully! 🎉",
                "post": {
                    "id":        post.id,
                    "image_url": post.image.url,
                    "caption":   post.caption,
                    "username":  request.user.username,
                }
            })

        messages.success(request, "Post shared successfully! 🎉")

    return redirect("home")



# =========================
# LIKE POST
# =========================

@login_required
def like_post(request, post_id):

    post = get_object_or_404(Post, id=post_id)

    like = Like.objects.filter(user=request.user, post=post)

    if like.exists():
        like.delete()
    else:
        Like.objects.create(user=request.user, post=post)

        if post.user != request.user:
            Notification.objects.create(
                sender=request.user,
                receiver=post.user,
                post=post,
                notif_type="like"
            )

    return redirect("home")


# =========================
# COMMENT
# =========================

@login_required
def add_comment(request, post_id):

    if request.method == "POST":

        post = get_object_or_404(Post, id=post_id)

        text = request.POST.get("text")

        if text:

            Comment.objects.create(
                user=request.user,
                post=post,
                text=text
            )

            if post.user != request.user:
                Notification.objects.create(
                    sender=request.user,
                    receiver=post.user,
                    post=post,
                    notif_type="comment"
                )

    return redirect("home")


# =========================
# SAVE POST
# =========================

@login_required
def save_post(request, post_id):

    post = get_object_or_404(Post, id=post_id)

    if request.user in post.saved_by.all():
        post.saved_by.remove(request.user)
    else:
        post.saved_by.add(request.user)

    return redirect("home")


# =========================
# FOLLOW USER
# =========================

@login_required
def follow_user(request, username):

    user_to_follow = get_object_or_404(User, username=username)

    if user_to_follow == request.user:
        return redirect("home")

    # Create FollowRequest only if it doesn't already exist
    freq, created = FollowRequest.objects.get_or_create(
        sender=request.user,
        receiver=user_to_follow
    )

    # Only send notification if this is a brand-new request
    if created:
        Notification.objects.get_or_create(
            sender=request.user,
            receiver=user_to_follow,
            notif_type="follow_request",
            defaults={"is_read": False}
        )

    return redirect("home")


# =========================
# ACCEPT FOLLOW REQUEST
# =========================

@login_required
def accept_follow_request(request, request_id):

    follow_request = get_object_or_404(FollowRequest, id=request_id, receiver=request.user)

    # Use get_or_create to avoid duplicate Follow records
    Follow.objects.get_or_create(
        follower=follow_request.sender,
        following=follow_request.receiver
    )

    # Notify the sender that their request was accepted
    Notification.objects.get_or_create(
        sender=follow_request.receiver,
        receiver=follow_request.sender,
        notif_type="follow"
    )

    # Remove the original follow_request notification (no longer pending)
    Notification.objects.filter(
        sender=follow_request.sender,
        receiver=follow_request.receiver,
        notif_type="follow_request"
    ).delete()

    follow_request.delete()

    return redirect("home")


# =========================
# DECLINE FOLLOW REQUEST
# =========================

@login_required
def decline_follow_request(request, request_id):

    follow_request = get_object_or_404(FollowRequest, id=request_id, receiver=request.user)

    # Remove the associated follow_request notification
    Notification.objects.filter(
        sender=follow_request.sender,
        receiver=follow_request.receiver,
        notif_type="follow_request"
    ).delete()

    follow_request.delete()

    return redirect("home")


# =========================
# MESSAGES
# =========================

@login_required
def messages_view(request):
    me = request.user

    # Find all users me has had a conversation with
    from django.db.models import Q, Max
    partner_ids = (
        Message.objects
        .filter(Q(sender=me) | Q(receiver=me))
        .values_list('sender_id', 'receiver_id')
    )
    seen = set()
    for s, r in partner_ids:
        other = r if s == me.id else s
        seen.add(other)

    partners = User.objects.filter(id__in=seen)
    return render(request, 'message.html', {'partners': partners})


@login_required
def get_conversations(request):
    """Return JSON list of conversations (latest message per partner)."""
    from django.db.models import Q
    me = request.user

    all_msgs = (
        Message.objects
        .filter(Q(sender=me) | Q(receiver=me))
        .order_by('-created_at')
    )

    seen = {}
    for msg in all_msgs:
        other = msg.receiver if msg.sender_id == me.id else msg.sender
        if other.id not in seen:
            seen[other.id] = {
                'username':   other.username,
                'full_name':  other.get_full_name() or other.username,
                'avatar_url': other.profile.profile_image.url if hasattr(other, 'profile') and other.profile.profile_image else None,
                'preview':    ('You: ' if msg.sender_id == me.id else '') + msg.text[:60],
                'time':       msg.created_at.strftime('%H:%M'),
                'unread':     msg.receiver_id == me.id and not msg.is_read,
            }

    return JsonResponse({'conversations': list(seen.values())})


@login_required
def get_messages(request, username):
    """Return JSON list of messages between me and <username>. Marks them as read."""
    from django.db.models import Q
    me = request.user
    other = get_object_or_404(User, username=username)

    msgs = Message.objects.filter(
        Q(sender=me, receiver=other) | Q(sender=other, receiver=me)
    ).order_by('created_at')

    # Mark incoming messages as read
    msgs.filter(receiver=me, is_read=False).update(is_read=True)

    data = [{
        'id':         m.id,
        'text':       m.text,
        'out':        m.sender_id == me.id,
        'time':       m.created_at.strftime('%H:%M'),
        'sender':     m.sender.username,
        'is_read':    m.is_read,
    } for m in msgs]

    other_info = {
        'username':   other.username,
        'full_name':  other.get_full_name() or other.username,
        'avatar_url': other.profile.profile_image.url if hasattr(other, 'profile') and other.profile.profile_image else None,
    }

    return JsonResponse({'messages': data, 'other': other_info})


@login_required
def send_message(request, username):
    """POST — save a new message to DB."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    import json
    me = request.user
    other = get_object_or_404(User, username=username)

    try:
        body = json.loads(request.body)
        text = body.get('text', '').strip()
    except Exception:
        text = request.POST.get('text', '').strip()

    if not text:
        return JsonResponse({'error': 'Empty message'}, status=400)

    msg = Message.objects.create(sender=me, receiver=other, text=text)
    return JsonResponse({
        'id':      msg.id,
        'text':    msg.text,
        'out':     True,
        'time':    msg.created_at.strftime('%H:%M'),
        'is_read': False,
    })


def search_view(request):
    q = request.GET.get('q', '').strip()
    return_json = request.GET.get('json') == '1'

    if return_json and q:
        users = User.objects.filter(username__icontains=q).exclude(id=request.user.id)[:10]
        data = []
        for u in users:
            data.append({
                'username':  u.username,
                'full_name': u.get_full_name() or u.username,
                'avatar_url': u.profile.profile_image.url
                               if hasattr(u, 'profile') and u.profile.profile_image else None,
            })
        return JsonResponse({'users': data})

    return render(request, 'search.html', {'query': q})



def suggested_users_view(request):
    return render(request, 'suggested_users.html')


def switch_account_view(request):
    return redirect('login')


# Temporary debug endpoint — remove after confirming Cloudinary works
def debug_storage(request):
    import os
    from django.core.files.storage import default_storage
    from django.conf import settings
    data = {
        'storage_class':      type(default_storage).__name__,
        'CLOUDINARY_URL_set': bool(os.environ.get('CLOUDINARY_URL')),
        'DEFAULT_FILE_STORAGE': getattr(settings, 'DEFAULT_FILE_STORAGE', 'not set'),
        'CLOUDINARY_STORAGE':   getattr(settings, 'CLOUDINARY_STORAGE', 'not set'),
        'MEDIA_URL':            settings.MEDIA_URL,
    }
    return JsonResponse(data)



def switch_account_view(request):
    return redirect('login')
