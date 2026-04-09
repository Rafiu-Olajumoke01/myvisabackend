from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/packages/', include('packages.urls')),  
    path('api/bookmarks/', include('bookmarks.urls')), 
    path('api/reviews/', include('reviews.urls')),  
    path('api/applications/', include('applications.urls')), 
    path('api/calls/', include('calls.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "MyVisa Admin Panel"
admin.site.site_title = "MyVisa Admin"
admin.site.index_title = "Welcome to MyVisa Administration"
