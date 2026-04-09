# reviews/urls.py
from django.urls import path
from .views import (
    ReviewListView,
    ReviewCreateView,
    ReviewUpdateView,
    ReviewDeleteView,
    PackageRatingView
)

urlpatterns = [
    path('', ReviewListView.as_view(), name='review-list'),
    path('create/', ReviewCreateView.as_view(), name='review-create'),
    path('<int:id>/', ReviewUpdateView.as_view(), name='review-update'),
    path('<int:id>/delete/', ReviewDeleteView.as_view(), name='review-delete'),
    path('rating/', PackageRatingView.as_view(), name='package-rating'),
]
