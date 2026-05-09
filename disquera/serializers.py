from rest_framework import serializers
from .models import Album, AlbumDirectory, MusicWatcher, MusicWishlist, MusicInbox, MusicAnnualRecord


class AlbumDirectorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AlbumDirectory
        fields = '__all__'


class AlbumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = '__all__'


class MusicWatcherSerializer(serializers.ModelSerializer):
    class Meta:
        model = MusicWatcher
        fields = '__all__'


class MusicWishlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = MusicWishlist
        fields = '__all__'


class MusicInboxSerializer(serializers.ModelSerializer):
    class Meta:
        model = MusicInbox
        fields = '__all__'


class MusicAnnualRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MusicAnnualRecord
        fields = '__all__'
