from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'albums', views.AlbumViewSet, basename='album')
router.register(r'directories', views.AlbumDirectoryViewSet,
                basename='albumdirectory')
router.register(r'watchers', views.MusicWatcherViewSet,
                basename='musicwatcher')
router.register(r'wishlist', views.MusicWishlistViewSet,
                basename='musicwishlist')
router.register(r'inbox', views.MusicInboxViewSet, basename='musicinbox')
router.register(r'tracker/log', views.ListeningEntryViewSet, basename='musictrackerlog')

urlpatterns = [
    path('', include(router.urls)),
    path('scan/', views.scan_album, name='scan-album'),
    path('process-barcode/', views.process_barcode, name='process-barcode'),
    path('tracker/', views.tracker_stats, name='tracker-stats'),
    path('tracker/annual/', views.tracker_annual, name='tracker-annual'),
    path('tracker/finish/', views.finish_album, name='finish-album'),
    path('tracker/annual/<int:pk>/', views.delete_annual_record,
         name='delete-annual-record'),
]
