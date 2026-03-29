from rest_framework import serializers
from .models import Book, Author, Genre, Watcher, WishlistItem, Friend, Loan, Directory, ScanInbox
from .models import AnnualRecord


class BookSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)

    # Campo calculado para que el CLI lea los géneros
    genre_list = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = '__all__'

    def get_genre_list(self, obj):
        return [g.name for g in obj.genres.all()]

    def create(self, validated_data):
        author_input = validated_data.pop('author_input', None)
        genre_input = validated_data.pop(
            'genre_input', None)

        # Guardado del autor
        if author_input:
            author, _ = Author.objects.get_or_create(name=author_input.strip())
            validated_data['author'] = author

        # Creamos el libro
        book = super().create(validated_data)

        # Si el usuario escribió géneros manualmente, lo conecta
        if genre_input:
            genres = [g.strip() for g in genre_input.split(',') if g.strip()]
            for g_name in genres:
                genre, _ = Genre.objects.get_or_create(name=g_name)
                book.genres.add(genre)

        return book

    def update(self, instance, validated_data):
        author_input = validated_data.pop('author_input', None)
        genre_input = validated_data.pop(
            'genre_input', None)

        if author_input:
            author, _ = Author.objects.get_or_create(name=author_input.strip())
            instance.author = author

        # Si el usuario edita los géneros, reescribe la relación Many-to-Many
        if genre_input is not None:
            genres = [g.strip() for g in genre_input.split(',') if g.strip()]
            genre_objs = []
            for g_name in genres:
                genre, _ = Genre.objects.get_or_create(name=g_name)
                genre_objs.append(genre)
            instance.genres.set(genre_objs)

        return super().update(instance, validated_data)


class WatcherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Watcher
        fields = '__all__'


class WishlistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WishlistItem
        fields = '__all__'


class FriendSerializer(serializers.ModelSerializer):
    class Meta:
        model = Friend
        fields = '__all__'


class LoanSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title', read_only=True)
    friend_name = serializers.CharField(source='friend.name', read_only=True)

    class Meta:
        model = Loan
        fields = '__all__'


class AnnualRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnualRecord
        fields = '__all__'


class DirectorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Directory
        fields = '__all__'


class ScanInboxSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanInbox
        fields = '__all__'
