from django.contrib import admin
from django.urls import path, include
from catalog.views import scanner_view

urlpatterns = [
    path('admin/', admin.site.urls),
    # Conecta el endpoint a la ruta principal
    path('api/books/', include('catalog.urls')),
    path('scanner/', scanner_view, name='scanner'),
]
