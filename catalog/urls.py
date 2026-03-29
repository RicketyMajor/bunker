from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import log_pages, finish_book, tracker_stats, AnnualRecordViewSet

#  enrutador y registra las nuevas vistas automáticas
router = DefaultRouter()
router.register(r'library', views.BookViewSet, basename='library')
router.register(r'watchers-crud', views.WatcherViewSet,
                basename='watcher-crud')
router.register(r'wishlist-crud', views.WishlistItemViewSet,
                basename='wishlist-crud')
router.register(r'friends', views.FriendViewSet, basename='friends')
router.register(r'loans', views.LoanViewSet, basename='loans')
router.register(r'tracker/annual', AnnualRecordViewSet,
                basename='tracker-annual')
router.register(r'directories', views.DirectoryViewSet, basename='directories')

urlpatterns = [
    # endpoints
    path('scan/', views.scan_book, name='scan-book'),
    path('scanner/', views.scanner_view, name='scanner-ui'),
    path('watchers/', views.get_active_watchers, name='watchers-list'),
    path('wishlist/add/', views.add_wishlist_item, name='wishlist-add'),
    path('tracker/pages/', log_pages, name='log-pages'),
    path('tracker/finish/', finish_book, name='finish-book'),
    path('tracker/stats/', tracker_stats, name='tracker-stats'),

    # Inyecta todas las rutas automáticas generadas por el router
    path('', include(router.urls)),
]
