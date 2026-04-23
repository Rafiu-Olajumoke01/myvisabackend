# reviews/urls.py
from django.urls import path
from .views import (
    ReviewListView,
    ReviewCreateView,
    ReviewUpdateView,
    ReviewDeleteView,
    PackageRatingView,
    SPReviewListView,
    SPReviewCreateView,
    SPReviewDeleteView,
)

urlpatterns = [
    # Package review endpoints
    path('', ReviewListView.as_view(), name='review-list'),
    path('create/', ReviewCreateView.as_view(), name='review-create'),
    path('<int:id>/', ReviewUpdateView.as_view(), name='review-update'),
    path('<int:id>/delete/', ReviewDeleteView.as_view(), name='review-delete'),
    path('rating/', PackageRatingView.as_view(), name='package-rating'),

    # SP review endpoints
    path('sp/', SPReviewListView.as_view(), name='sp-review-list'),
    path('sp/create/', SPReviewCreateView.as_view(), name='sp-review-create'),
    path('sp/<str:id>/', SPReviewDeleteView.as_view(), name='sp-review-delete'),
]