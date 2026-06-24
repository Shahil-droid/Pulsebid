from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # Connects to your app1 urls
    path('', include('app1.urls')),
]

# This block is REQUIRED to display uploaded images (Profile Pics)
# It only runs when you are in Debug mode (developing on your computer)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)