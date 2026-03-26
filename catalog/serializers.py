from rest_framework import serializers
from .models import Book, Author, Genre, Watcher, WishlistItem, Friend, Loan, Directory
from .models import AnnualRecord


class BookSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)
    # 🚀 Campo virtual para recibir el nombre del autor como texto desde el CLI
    author_input = serializers.CharField(
        write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Book
        fields = '__all__'
        # Evitamos que DRF nos exija el ID (PK) original
        extra_kwargs = {'author': {'read_only': True}}

    def create(self, validated_data):
        # 1. Extraemos el texto del autor antes de guardar el libro
        author_name = validated_data.pop('author_input', None)

        # 2. Si viene un nombre, aplicamos la lógica "get_or_create"
        if author_name:
            author, _ = Author.objects.get_or_create(name=author_name.strip())
            validated_data['author'] = author

        # 3. Guardamos el libro normalmente con el autor ya asignado
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # 1. Extraemos el author_input si el usuario lo envió en el PATCH
        author_input = validated_data.pop('author_input', None)

        # 2. Si hay un autor nuevo, lo buscamos o lo creamos, y se lo asignamos a la instancia
        if author_input:
            # Asegúrate de que el modelo Author esté importado
            author, created = Author.objects.get_or_create(
                name=author_input.strip())
            instance.author = author

        # 3. Continuamos con la actualización normal del resto de los campos
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
