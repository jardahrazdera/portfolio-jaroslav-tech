from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('search/', views.search, name='search'),
    path('post/<slug:slug>/', views.post_detail, name='post_detail'),
    path('category/<slug:slug>/', views.category_list, name='category_list'),
    path('tag/<slug:slug>/', views.tag_list, name='tag_list'),
    path('download/<int:file_id>/', views.download_file, name='download_file'),
    path('embed-demo/', views.embed_demo, name='embed_demo'),
    path('embed-guide/', views.embed_guide, name='embed_guide'),
    path('saved/', views.saved_posts, name='saved_posts'),

    # Newsletter URLs
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    path('newsletter/success/', views.newsletter_success, name='newsletter_success'),
    path('newsletter/unsubscribe/', views.newsletter_unsubscribe_general, name='newsletter_unsubscribe_general'),
    path('newsletter/confirm/<uuid:token>/', views.confirm_newsletter_subscription, name='confirm_subscription'),
    path('newsletter/unsubscribe/<uuid:token>/', views.unsubscribe_newsletter, name='unsubscribe'),

    # API endpoints
    path('api/track-share/', views.track_share, name='track_share'),
    path('api/track-related-click/', views.track_related_click, name='track_related_click'),
    path('api/related-posts/<slug:slug>/', views.related_posts_ajax, name='related_posts_ajax'),
    path('api/newsletter/subscribe/', views.newsletter_subscribe_ajax, name='newsletter_subscribe_ajax'),
]