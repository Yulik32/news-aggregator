from django.urls import path
from . import views

app_name = 'news'

urlpatterns = [
    path('', views.index, name='index'),
    path('article/<int:pk>/', views.article_detail, name='article_detail'),
    path('article/<int:pk>/save/', views.save_article, name='save_article'),
    path('saved/', views.saved_articles, name='saved_articles'),
    path('collections/', views.collections, name='collections'),
    path('collection/<int:pk>/', views.collection_detail, name='collection_detail'),
    path('collection/create/', views.create_collection, name='create_collection'),
    path('collection/<int:collection_id>/add/<int:article_id>/', views.add_to_collection, name='add_to_collection'),
    path('collection/<int:collection_id>/remove/<int:article_id>/', views.remove_from_collection, name='remove_from_collection'),
    path('collection/<int:pk>/delete/', views.delete_collection, name='delete_collection'),
    path('filter/save/', views.save_filter, name='save_filter'),
    path('subscribe/', views.subscribe, name='subscribe'),
    path('sources/', views.sources, name='sources'),
    path('source/<int:pk>/', views.source_detail, name='source_detail'),
    path('api/search/suggestions/', views.search_suggestions, name='search_suggestions'),
]