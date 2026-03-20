"""
views.py – Production-ready Instagram Clone views.

Changes from original:
  - Feed now shows only followed users' posts (+ own posts) with pagination
  - follow_user   : direct-follow for public accounts; FollowRequest for private
  - unfollow_user : new view
  - like_post     : AJAX-capable (returns JSON when X-Requested-With set)
  - save_post     : AJAX-capable
  - profile_edit  : new view
  - explore_view  : new view (posts ordered by like count)
  - saved_posts_view : new view
  - notifications_view / mark_notification_read : new views
  - delete_post   : new view (owner-only)
  - Fixed duplicate switch_account_view
  - Added @login_required to search_view
  - select_related / prefetch_related throughout to kill N+1 queries
  - Removed debug_storage endpoint (keep only if DEBUG)
"""

import re
import json

from django.contrib              import messages
from django.contrib.auth         import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models  import User
from django.core.paginator       import Paginator
from django.db.models            import Q, Count
from django.http                 import JsonResponse
from django.shortcuts            import render, redirect, get_object_or_404
from django.urls                 import reverse
from django.views.decorators.http import require_POST

from .forms  import ProfileEditForm, CommentForm
from .models import (
    Post, Like, Comment, Follow, FollowRequest,
    Notification, Message, Conversation, Profile,
)


# ═══════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════

def _is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _following_ids(user):
    """Return a flat list of IDs the *user* is following."""
    return list(
        Follow.objects.filter(follower=user).values_list('following_id', flat=True)
    )


def _sent_request_ids(user):
    """Return a flat list of IDs the *user* has a pending follow request to."""
    return list(
        FollowRequest.objects.filter(sender=user).values_list('receiver_id', flat=True)
    )


# ═══════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════

def register_view(request):

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':

        email    = request.POST.get('email',    '').strip()
        fullname = request.POST.get('fullname', '').strip()
        username = request.POST.get('username', '').strip().lower()
        password = request.POST.get('password', '')
        is_ajax  = _is_ajax(request)

        def err(msg, field=None):
            if is_ajax:
                return JsonResponse({'success': False, 'error': msg, 'field': field})
            messages.error(request, msg)
            return redirect('register')

        if not email:
            return err('Please enter your email.', 'email')
        if not fullname:
            return err('Please enter your full name.', 'fullname')
        if not username:
            return err('Please enter a username.', 'username')
        if not password:
            return err('Please enter a password.', 'password')
        if len(password) < 6:
            return err('Password must be at least 6 characters.', 'password')
        if not re.match(r'^[a-z0-9._]{3,30}$', username):
            return err('Username must be 3–30 chars: letters, numbers, . or _', 'username')
        if User.objects.filter(username=username).exists():
            return err('That username is already taken.', 'username')
        if User.objects.filter(email__iexact=email).exists():
            return err('An account with that email already exists.', 'email')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.first_name = fullname
        user.save()
        login(request, user)

        if is_ajax:
            return JsonResponse({'success': True, 'redirect': reverse('home')})

        messages.success(request, f"Welcome to Instagram, @{username}! 🎉")
        return redirect('home')

    return render(request, 'signup.html')


def login_view(request):

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        is_ajax  = _is_ajax(request)

        if not username and not password:
            error = 'Please enter your username and password.'
        elif not username:
            error = 'Please enter your username or email.'
        elif not password:
            error = 'Please enter your password.'
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if is_ajax:
                    return JsonResponse({'success': True, 'redirect': reverse('home')})
                return redirect('home')
            else:
                error = 'Sorry, your password was incorrect.'

        if is_ajax:
            return JsonResponse({'success': False, 'error': error})
        messages.error(request, error)
        return redirect('login')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')


# ═══════════════════════════════════════════════
#  CHECK AVAILABILITY (AJAX)
# ═══════════════════════════════════════════════

def check_availability(request):
    """GET /check-availability/?type=username&value=john"""
    check_type = request.GET.get('type', '')
    value      = request.GET.get('value', '').strip()

    if not value:
        return JsonResponse({'available': True})

    if check_type == 'username':
        exists = User.objects.filter(username__iexact=value).exists()
    elif check_type == 'email':
        exists = User.objects.filter(email__iexact=value).exists()
    else:
        return JsonResponse({'error': 'Invalid type'}, status=400)

    return JsonResponse({'available': not exists})


# ═══════════════════════════════════════════════
#  HOME FEED
# ═══════════════════════════════════════════════

@login_required
def home_view(request):
    me = request.user

    # ── Followed-users-only feed ──
    followed_ids = _following_ids(me)
    # Include own posts so the feed isn't empty when you don't follow anyone
    feed_ids = followed_ids + [me.id]

    posts_qs = (
        Post.objects
        .filter(user_id__in=feed_ids)
        .select_related('user', 'user__profile')
        .prefetch_related('likes', 'comments__user', 'saved_by')
        .order_by('-created_at')
    )

    paginator = Paginator(posts_qs, 12)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    # ── Sidebar data ──
    sent_req_ids = _sent_request_ids(me)
    follower_ids = list(
        Follow.objects.filter(following=me).values_list('follower_id', flat=True)
    )

    follow_requests = (
        FollowRequest.objects
        .filter(receiver=me)
        .select_related('sender', 'sender__profile')
    )

    notifications = (
        Notification.objects
        .filter(receiver=me)
        .select_related('sender', 'sender__profile', 'post')
        .order_by('-created_at')[:20]
    )
    unread_notifications_count = Notification.objects.filter(receiver=me, is_read=False).count()

    suggested_users = (
        User.objects
        .exclude(id=me.id)
        .exclude(id__in=followed_ids)
        .exclude(id__in=sent_req_ids)
        .select_related('profile')
        [:5]
    )

    # IDs the current user has liked — used by templates to show filled heart
    liked_ids = set(
        Like.objects.filter(user=me, post__in=page_obj.object_list).values_list('post_id', flat=True)
    )
    saved_ids = set(
        me.saved_posts.filter(id__in=[p.id for p in page_obj.object_list]).values_list('id', flat=True)
    )

    context = {
        'page_obj':                  page_obj,
        'posts':                     page_obj.object_list,
        'follow_requests':           follow_requests,
        'notifications':             notifications,
        'unread_notifications_count': unread_notifications_count,
        'suggested_users':           suggested_users,
        'following_ids':             followed_ids,
        'sent_request_ids':          sent_req_ids,
        'follower_ids':              follower_ids,
        'liked_ids':                 liked_ids,
        'saved_ids':                 saved_ids,
    }

    return render(request, 'homepage.html', context)


# ═══════════════════════════════════════════════
#  PROFILE
# ═══════════════════════════════════════════════

@login_required
def profile_view(request, username):
    profile_user = get_object_or_404(
        User.objects.select_related('profile'), username=username
    )

    posts = (
        Post.objects
        .filter(user=profile_user)
        .prefetch_related('likes', 'comments')
        .order_by('-created_at')
    )

    followers_qs = Follow.objects.filter(following=profile_user).select_related('follower', 'follower__profile')
    following_qs = Follow.objects.filter(follower=profile_user).select_related('following', 'following__profile')

    followers_list = [f.follower  for f in followers_qs]
    following_list = [f.following for f in following_qs]

    is_following    = Follow.objects.filter(follower=request.user, following=profile_user).exists()
    has_sent_request = FollowRequest.objects.filter(sender=request.user, receiver=profile_user).exists()

    # Privacy: hide posts grid for private accounts unless following
    can_see_posts = (
        not profile_user.profile.private_account
        or profile_user == request.user
        or is_following
    )

    context = {
        'profile_user':     profile_user,
        'posts':            posts if can_see_posts else [],
        'can_see_posts':    can_see_posts,
        'followers_list':   followers_list,
        'following_list':   following_list,
        'followers_count':  len(followers_list),
        'following_count':  len(following_list),
        'is_following':     is_following,
        'has_sent_request': has_sent_request,
        'post_count':       posts.count(),
    }

    return render(request, 'profile.html', context)


@login_required
def profile_edit(request):
    """Edit the logged-in user's profile (bio, image, website, privacy)."""
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # Also allow updating display name from this form
        fullname = request.POST.get('fullname', '').strip()
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            if fullname:
                request.user.first_name = fullname
                request.user.save(update_fields=['first_name'])
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile', username=request.user.username)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = ProfileEditForm(instance=profile)

    return render(request, 'profile_edit.html', {
        'form': form,
        'profile': profile,
    })


# ═══════════════════════════════════════════════
#  CREATE / DELETE POST
# ═══════════════════════════════════════════════

@login_required
def create_post(request):

    if request.method == 'POST':
        image    = request.FILES.get('image')
        caption  = request.POST.get('caption', '').strip()
        location = request.POST.get('location', '').strip()
        is_ajax  = _is_ajax(request)

        if not image:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Please select an image.'})
            messages.error(request, 'Please select an image.')
            return redirect('home')

        # Basic size guard (10 MB)
        if image.size > 10 * 1024 * 1024:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Image must be smaller than 10 MB.'})
            messages.error(request, 'Image must be smaller than 10 MB.')
            return redirect('home')

        post = Post.objects.create(
            user=request.user,
            image=image,
            caption=caption,
            location=location,
        )

        if is_ajax:
            return JsonResponse({
                'success':   True,
                'message':   'Post shared successfully! 🎉',
                'post': {
                    'id':        post.id,
                    'image_url': post.image.url,
                    'caption':   post.caption,
                    'username':  request.user.username,
                },
            })

        messages.success(request, 'Post shared successfully! 🎉')

    return redirect('home')


@login_required
@require_POST
def delete_post(request, post_id):
    """Delete a post — only the owner can do this."""
    post = get_object_or_404(Post, id=post_id, user=request.user)
    post.delete()
    if _is_ajax(request):
        return JsonResponse({'success': True})
    messages.success(request, 'Post deleted.')
    return redirect('profile', username=request.user.username)


# ═══════════════════════════════════════════════
#  LIKE POST  (AJAX-capable)
# ═══════════════════════════════════════════════

@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like = Like.objects.filter(user=request.user, post=post)

    if like.exists():
        like.delete()
        liked = False
    else:
        Like.objects.create(user=request.user, post=post)
        liked = True
        # Notify post owner (not self)
        if post.user != request.user:
            Notification.objects.get_or_create(
                sender=request.user,
                receiver=post.user,
                post=post,
                notif_type='like',
            )

    like_count = post.likes.count()

    if _is_ajax(request):
        return JsonResponse({'liked': liked, 'like_count': like_count})

    return redirect(request.META.get('HTTP_REFERER', 'home'))


# ═══════════════════════════════════════════════
#  COMMENT
# ═══════════════════════════════════════════════

@login_required
@require_POST
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    text = request.POST.get('text', '').strip()

    if not text:
        if _is_ajax(request):
            return JsonResponse({'success': False, 'error': 'Comment cannot be empty.'}, status=400)
        return redirect(request.META.get('HTTP_REFERER', 'home'))

    # Limit comment length
    if len(text) > 2200:
        text = text[:2200]

    comment = Comment.objects.create(user=request.user, post=post, text=text)

    if post.user != request.user:
        Notification.objects.get_or_create(
            sender=request.user,
            receiver=post.user,
            post=post,
            notif_type='comment',
        )

    if _is_ajax(request):
        return JsonResponse({
            'success':  True,
            'comment': {
                'id':       comment.id,
                'text':     comment.text,
                'username': request.user.username,
                'avatar':   (
                    request.user.profile.profile_image.url
                    if hasattr(request.user, 'profile') and request.user.profile.profile_image
                    else None
                ),
            },
        })

    return redirect(request.META.get('HTTP_REFERER', 'home'))


# ═══════════════════════════════════════════════
#  SAVE POST  (AJAX-capable)
# ═══════════════════════════════════════════════

@login_required
def save_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.user in post.saved_by.all():
        post.saved_by.remove(request.user)
        saved = False
    else:
        post.saved_by.add(request.user)
        saved = True

    if _is_ajax(request):
        return JsonResponse({'saved': saved})

    return redirect(request.META.get('HTTP_REFERER', 'home'))


# ═══════════════════════════════════════════════
#  FOLLOW / UNFOLLOW
# ═══════════════════════════════════════════════

@login_required
def follow_user(request, username):
    user_to_follow = get_object_or_404(User, username=username)

    if user_to_follow == request.user:
        return redirect('profile', username=username)

    # Already following? Do nothing.
    if Follow.objects.filter(follower=request.user, following=user_to_follow).exists():
        return redirect(request.META.get('HTTP_REFERER', 'home'))

    profile = getattr(user_to_follow, 'profile', None)
    is_private = profile.private_account if profile else False

    if is_private:
        # Send follow request — get_or_create prevents duplicates
        freq, created = FollowRequest.objects.get_or_create(
            sender=request.user,
            receiver=user_to_follow,
        )
        if created:
            Notification.objects.get_or_create(
                sender=request.user,
                receiver=user_to_follow,
                notif_type='follow_request',
                defaults={'is_read': False},
            )
    else:
        # Public account — direct follow
        Follow.objects.get_or_create(follower=request.user, following=user_to_follow)
        Notification.objects.get_or_create(
            sender=request.user,
            receiver=user_to_follow,
            notif_type='follow',
            defaults={'is_read': False},
        )

    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def unfollow_user(request, username):
    user_to_unfollow = get_object_or_404(User, username=username)
    Follow.objects.filter(follower=request.user, following=user_to_unfollow).delete()

    if _is_ajax(request):
        return JsonResponse({'unfollowed': True})

    return redirect(request.META.get('HTTP_REFERER', 'home'))


# ═══════════════════════════════════════════════
#  ACCEPT / DECLINE FOLLOW REQUEST
# ═══════════════════════════════════════════════

@login_required
def accept_follow_request(request, request_id):
    follow_request = get_object_or_404(FollowRequest, id=request_id, receiver=request.user)

    Follow.objects.get_or_create(
        follower=follow_request.sender,
        following=follow_request.receiver,
    )

    Notification.objects.get_or_create(
        sender=follow_request.receiver,
        receiver=follow_request.sender,
        notif_type='follow',
    )

    # Remove the pending follow_request notification
    Notification.objects.filter(
        sender=follow_request.sender,
        receiver=follow_request.receiver,
        notif_type='follow_request',
    ).delete()

    follow_request.delete()

    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def decline_follow_request(request, request_id):
    follow_request = get_object_or_404(FollowRequest, id=request_id, receiver=request.user)

    Notification.objects.filter(
        sender=follow_request.sender,
        receiver=follow_request.receiver,
        notif_type='follow_request',
    ).delete()

    follow_request.delete()

    return redirect(request.META.get('HTTP_REFERER', 'home'))


# ═══════════════════════════════════════════════
#  NOTIFICATIONS
# ═══════════════════════════════════════════════

@login_required
def notifications_view(request):
    notifs = (
        Notification.objects
        .filter(receiver=request.user)
        .select_related('sender', 'sender__profile', 'post')
        .order_by('-created_at')
    )
    # Mark all as read on page visit
    notifs.filter(is_read=False).update(is_read=True)

    return render(request, 'notifications.html', {'notifications': notifs})


@login_required
def mark_notification_read(request, notif_id):
    """AJAX endpoint to mark a single notification as read."""
    Notification.objects.filter(id=notif_id, receiver=request.user).update(is_read=True)
    return JsonResponse({'success': True})


# ═══════════════════════════════════════════════
#  EXPLORE
# ═══════════════════════════════════════════════

@login_required
def explore_view(request):
    """Show trending public posts (ordered by like count), paginated."""
    posts_qs = (
        Post.objects
        .annotate(like_count=Count('likes'))
        .select_related('user', 'user__profile')
        .prefetch_related('likes', 'comments')
        .order_by('-like_count', '-created_at')
    )
    paginator = Paginator(posts_qs, 24)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    liked_ids = set(
        Like.objects.filter(user=request.user, post__in=page_obj.object_list).values_list('post_id', flat=True)
    )
    saved_ids = set(
        request.user.saved_posts.filter(
            id__in=[p.id for p in page_obj.object_list]
        ).values_list('id', flat=True)
    )

    return render(request, 'explore.html', {
        'page_obj':  page_obj,
        'posts':     page_obj.object_list,
        'liked_ids': liked_ids,
        'saved_ids': saved_ids,
    })


# ═══════════════════════════════════════════════
#  SAVED POSTS
# ═══════════════════════════════════════════════

@login_required
def saved_posts_view(request):
    posts_qs = (
        request.user.saved_posts
        .select_related('user', 'user__profile')
        .prefetch_related('likes', 'comments')
        .order_by('-created_at')
    )
    paginator = Paginator(posts_qs, 12)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'saved_posts.html', {
        'page_obj': page_obj,
        'posts':    page_obj.object_list,
    })


# ═══════════════════════════════════════════════
#  SEARCH
# ═══════════════════════════════════════════════

@login_required
def search_view(request):
    q           = request.GET.get('q', '').strip()
    return_json = request.GET.get('json') == '1'

    if return_json and q:
        users = (
            User.objects
            .filter(Q(username__icontains=q) | Q(first_name__icontains=q))
            .exclude(id=request.user.id)
            .select_related('profile')
            [:10]
        )
        data = [{
            'username':   u.username,
            'full_name':  u.get_full_name() or u.username,
            'avatar_url': (
                u.profile.profile_image.url
                if hasattr(u, 'profile') and u.profile.profile_image else None
            ),
        } for u in users]
        return JsonResponse({'users': data})

    return render(request, 'search.html', {'query': q})


# ═══════════════════════════════════════════════
#  MESSAGES / CONVERSATIONS
# ═══════════════════════════════════════════════

@login_required
def messages_view(request):
    me = request.user

    partner_ids = (
        Message.objects
        .filter(Q(sender=me) | Q(receiver=me))
        .values_list('sender_id', 'receiver_id')
    )
    seen = set()
    for s, r in partner_ids:
        other = r if s == me.id else s
        seen.add(other)

    partners = User.objects.filter(id__in=seen).select_related('profile')
    return render(request, 'message.html', {'partners': partners})


@login_required
def get_conversations(request):
    """Return JSON list of conversations (latest message per partner)."""
    me = request.user

    all_msgs = (
        Message.objects
        .filter(Q(sender=me) | Q(receiver=me))
        .select_related('sender', 'sender__profile', 'receiver', 'receiver__profile')
        .order_by('-created_at')
    )

    seen = {}
    for msg in all_msgs:
        other = msg.receiver if msg.sender_id == me.id else msg.sender
        if other.id not in seen:
            seen[other.id] = {
                'username':   other.username,
                'full_name':  other.get_full_name() or other.username,
                'avatar_url': (
                    other.profile.profile_image.url
                    if hasattr(other, 'profile') and other.profile.profile_image else None
                ),
                'preview': ('You: ' if msg.sender_id == me.id else '') + msg.text[:60],
                'time':    msg.created_at.strftime('%H:%M'),
                'unread':  msg.receiver_id == me.id and not msg.is_read,
            }

    return JsonResponse({'conversations': list(seen.values())})


@login_required
def get_messages(request, username):
    """Return JSON messages between me and <username>. Marks them as read."""
    me    = request.user
    other = get_object_or_404(User, username=username)

    msgs = (
        Message.objects
        .filter(Q(sender=me, receiver=other) | Q(sender=other, receiver=me))
        .select_related('sender')
        .order_by('created_at')
    )

    # Mark incoming as read
    msgs.filter(receiver=me, is_read=False).update(is_read=True)

    data = [{
        'id':      m.id,
        'text':    m.text,
        'out':     m.sender_id == me.id,
        'time':    m.created_at.strftime('%H:%M'),
        'sender':  m.sender.username,
        'is_read': m.is_read,
    } for m in msgs]

    other_info = {
        'username':   other.username,
        'full_name':  other.get_full_name() or other.username,
        'avatar_url': (
            other.profile.profile_image.url
            if hasattr(other, 'profile') and other.profile.profile_image else None
        ),
    }

    return JsonResponse({'messages': data, 'other': other_info})


@login_required
@require_POST
def send_message(request, username):
    """POST — save a new message to DB."""
    me    = request.user
    other = get_object_or_404(User, username=username)

    try:
        body = json.loads(request.body)
        text = body.get('text', '').strip()
    except Exception:
        text = request.POST.get('text', '').strip()

    if not text:
        return JsonResponse({'error': 'Empty message'}, status=400)

    # Limit message length
    if len(text) > 1000:
        return JsonResponse({'error': 'Message too long (max 1000 chars).'}, status=400)

    msg = Message.objects.create(sender=me, receiver=other, text=text)
    return JsonResponse({
        'id':      msg.id,
        'text':    msg.text,
        'out':     True,
        'time':    msg.created_at.strftime('%H:%M'),
        'is_read': False,
    })


# ═══════════════════════════════════════════════
#  MISC
# ═══════════════════════════════════════════════

def suggested_users_view(request):
    return render(request, 'suggested_users.html')


def switch_account_view(request):
    return redirect('login')
