# bookmarks/urls.py
from django.urls import path
from .views import (
    BookmarkListView,
    BookmarkCreateView,
    BookmarkDeleteView
)

urlpatterns = [
    path('', BookmarkListView.as_view(), name='bookmark-list'),
    path('create/', BookmarkCreateView.as_view(), name='bookmark-create'),
    path('<int:package_id>/', BookmarkDeleteView.as_view(), name='bookmark-delete'),
]
