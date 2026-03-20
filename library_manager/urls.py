from django.contrib import admin
from django.urls import path, include  # <-- Asegúrate de importar include
from catalog.views import scanner_view

urlpatterns = [
    path('admin/', admin.site.urls),
    # Conectamos nuestro endpoint a la ruta principal
    path('api/books/', include('catalog.urls')),
    path('scanner/', scanner_view, name='scanner'),
]
