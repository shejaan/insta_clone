from django.contrib import admin
from django.urls import path
from core import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [

    path('admin/', admin.site.urls),

    # HOME
    path('', views.home_view, name='home'),

    # AUTH
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('check-availability/', views.check_availability, name='check_availability'),

    # PROFILE
    path('profile/<str:username>/', views.profile_view, name='profile'),

    # POSTS
    path('create-post/', views.create_post, name='create_post'),
    path('like/<int:post_id>/', views.like_post, name='like_post'),
    path('comment/<int:post_id>/', views.add_comment, name='add_comment'),
    path('save/<int:post_id>/', views.save_post, name='save_post'),

    # FOLLOW
    path('follow/<str:username>/', views.follow_user, name='follow_user'),
    path('accept-follow/<int:request_id>/', views.accept_follow_request, name='accept_follow_request'),
    path('decline-follow/<int:request_id>/', views.decline_follow_request, name='decline_follow_request'),

    # EXTRA PAGES
    path('messages/', views.messages_view, name='messages'),
    path('messages/conversations/', views.get_conversations, name='get_conversations'),
    path('messages/with/<str:username>/', views.get_messages, name='get_messages'),
    path('messages/send/<str:username>/', views.send_message, name='send_message'),
    path('search/', views.search_view, name='search'),
    path('suggested-users/', views.suggested_users_view, name='suggested_users'),
    path('switch-account/', views.switch_account_view, name='switch_account'),


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)