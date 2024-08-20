from rest_framework import serializers

class FilmSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    genres = serializers.ListField()
    cast = serializers.ListField()
    runtime = serializers.FloatField()
    description = serializers.CharField()
    director = serializers.CharField(max_length=255)
    vote_average = serializers.FloatField()
    release_date = serializers.DateField()