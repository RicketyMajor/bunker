from django.contrib import admin
from django.urls import path, include  # <-- Asegúrate de importar include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Conectamos nuestro endpoint a la ruta principal
    path('api/books/', include('catalog.urls')),
]
