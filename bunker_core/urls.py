from django.contrib import admin
from django.urls import path, include
from catalog.views import scanner_view
from bunker_core.views import global_dashboard_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/books/', include('catalog.urls')),
    path('api/movies/', include('movies.urls')),
    path('scanner/', scanner_view, name='scanner'),
    path('api/dashboard/', global_dashboard_view, name='dashboard'),
    path('posada/', include('posada.urls')),
]
