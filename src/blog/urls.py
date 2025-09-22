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
]