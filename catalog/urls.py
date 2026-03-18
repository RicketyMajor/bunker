from django.urls import path
from . import views

urlpatterns = [
    path('scan/', views.scan_book, name='scan-book'),
    path('scanner/', views.scanner_view, name='scanner-ui'),

    # --- NUEVAS RUTAS PARA EL SCRAPER ---
    path('watchers/', views.get_active_watchers, name='watchers-list'),
    path('wishlist/add/', views.add_wishlist_item, name='wishlist-add'),
]
