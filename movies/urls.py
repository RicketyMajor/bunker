from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MovieViewSet, MovieDirectoryViewSet, MovieWatcherViewSet,
    MovieWishlistViewSet, MovieInboxViewSet,
    scan_movie, receive_barcode, process_barcode, movie_scanner_view,
    tracker_stats, tracker_annual, tracker_heatmap, log_minutes, finish_movie, delete_annual_record
)

router = DefaultRouter()
router.register(r'inventory', MovieViewSet, basename='movie')
router.register(r'directories', MovieDirectoryViewSet,
                basename='movie-directory')
router.register(r'watchers', MovieWatcherViewSet, basename='movie-watcher')
router.register(r'wishlist', MovieWishlistViewSet, basename='movie-wishlist')
router.register(r'inbox', MovieInboxViewSet, basename='movie-inbox')

urlpatterns = [
    path('scan/', scan_movie, name='scan-movie'),
    path('receive-barcode/', receive_barcode, name='receive-barcode'),
    path('process-barcode/', process_barcode, name='process-barcode'),
    path('scanner-web/', movie_scanner_view, name='movie-scanner-web'),
    path('tracker/stats/', tracker_stats, name='movie-tracker-stats'),
    path('tracker/annual/', tracker_annual, name='movie-tracker-annual'),
    path('tracker/heatmap/', tracker_heatmap, name='movie-tracker-heatmap'),
    path('tracker/minutes/', log_minutes, name='movie-log-minutes'),
    path('tracker/finish/', finish_movie, name='movie-finish'),
    path('tracker/annual/<int:pk>/', delete_annual_record,
         name='delete-annual-record'),
    path('', include(router.urls)),
]
