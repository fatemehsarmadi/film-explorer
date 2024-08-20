from django.forms import ValidationError
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework import status
from rest_framework import viewsets
from elasticsearch_dsl import Q, A
from . import serializers
from datetime import datetime
from films.aggregations import build_top_film_agg, build_popular_film_agg
from config.elasticsearch_config import search_index

INDEX_NAME = 'films'

class FilmViewSet(viewsets.ViewSet):
    def list(self, request):
        """
        Retrieves a list of films with optional filtering based on rating, runtime, and release date.
        """
        search = search_index(INDEX_NAME)

        params = request.GET
        rating_gte = params.get('rating_gte', '')
        runtime_lte = params.get('runtime_lte', '')
        release_year_gte = params.get('release_year_gte', '')
        release_year_lte = params.get('release_year_lte', '')

        filters = []

        if rating_gte:
            try:
                rating_gte = float(rating_gte)
                if rating_gte < 0 or rating_gte > 10:
                    raise ValidationError("Rating must be between 0 and 10.")
            except ValueError:
                raise ValidationError("Rating must be a number.")
            
            filters.append(
                Q('range', vote_average = {'gte': rating_gte})
            )
            
        if runtime_lte:
            try:
                runtime_lte = float(runtime_lte)
            except ValueError:
                raise ValidationError("Time must be a number.")
            
            filters.append(Q('range', runtime = {'lte': runtime_lte}))

        if release_year_gte or release_year_lte:
            year_filter = {}
            current_year = datetime.now().year

            if release_year_gte:
                try:
                    release_year_gte = int(release_year_gte)
                    if release_year_gte > current_year:
                        raise ValidationError(f"Year must not be in the future. Current year is {current_year}.")
                except ValueError:
                    raise ValidationError("Year must be a number.")
                year_filter['gte'] = f'{release_year_gte}-01-01'
            if release_year_lte:
                try:
                    release_year_lte = int(release_year_lte)
                except ValueError:
                    raise ValidationError("Year must be a number.")
                year_filter['lte'] = f'{release_year_lte}-12-31'

            filters.append(Q('range', release_date = year_filter))
            
        q = Q('bool', must = filters)
        search = search.query(q)

        response = search.execute()

        serializer = serializers.FilmSerializer(response, many = True)
        return Response(serializer.data)
    
    def top_films(self, request):
        """
        Returns a list of top films based on their rating, with optional filtering by genre and count.
        """
        search = search_index(INDEX_NAME)
        count = request.GET.get('count')
        genre = request.GET.get('genre')

        if count:
            try:
                count = int(count)
                if count < 1 or count > 15:
                    raise ValidationError("count must be between 1 and 15.")
            except ValueError:
                raise ValidationError("count must be a number.")
        else:
            count = 5

        if genre:
            search = search.query(Q('term', genres = genre))

        search = search.sort({
            '_script': {
                'type': 'number',
                'script': "doc['vote_average'].value * Math.log(doc['vote_count'].value)",
                'order': 'desc'
            }
        })
        search = search[:count]

        response = search.execute()
        serializer = serializers.FilmSerializer(response, many = True)

        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def genres(self, request):
        """
        Provides aggregated data on film genres, including average ratings, top films, and popular films within each genre.
        """
        search = search_index(INDEX_NAME)

        FIELD_GENRES = 'genres'
        FIELD_VOTE_AVERAGE = 'vote_average'
        FIELD_VOTE_COUNT = 'vote_count'
        FIELD_TITLE = 'title'

        genre_agg = A('terms', field = FIELD_GENRES, size = 10) \
            .metric(FIELD_VOTE_AVERAGE, A('avg', field = FIELD_VOTE_AVERAGE)) \
            .metric('top_film', build_top_film_agg()) \
            .metric('popular_film', build_popular_film_agg()) \
            .pipeline('sort_by_avg', A('bucket_sort', sort = [{FIELD_VOTE_AVERAGE: {'order': 'desc'}}]))
        search.aggs.bucket(FIELD_GENRES, genre_agg)

        response = search.execute()
        agg_result = []
        for bucket in response.aggregations.genres.buckets:
            agg_result.append({
                'genre': bucket.key,
                'film_count': bucket.doc_count,
                FIELD_VOTE_AVERAGE: round(bucket.vote_average.value, 2)
            })
            if bucket.top_film.hits.hits:
                top_film = bucket.top_film.hits.hits[0]._source
                agg_result[-1]['top_film'] = {
                    FIELD_TITLE: top_film[FIELD_TITLE],
                    FIELD_VOTE_AVERAGE: top_film[FIELD_VOTE_AVERAGE]
                }
            if bucket.popular_film.hits.hits:
                popular_film = bucket.popular_film.hits.hits[0]._source
                agg_result[-1]['popular_film'] = {
                    FIELD_TITLE: popular_film[FIELD_TITLE],
                    FIELD_VOTE_COUNT: int(popular_film[FIELD_VOTE_COUNT])
                }
        return Response(agg_result)
    
    @action(detail=False, methods=['get'])
    def directors(self, request):
        """
        Aggregates data on film directors, including average ratings of films directed by each director and the top film for each director.
        """
        search = search_index(INDEX_NAME)

        FIELD_VOTE_AVERAGE = 'vote_average'

        director_agg = A('terms', field = 'director.keyword') \
            .metric(FIELD_VOTE_AVERAGE, A('avg', field = FIELD_VOTE_AVERAGE)) \
            .metric('top_film', build_top_film_agg())
        search.aggs.bucket('directors', director_agg)

        response = search.execute()
        agg_result = []
        for bucket in response.aggregations.directors.buckets:
            agg_result.append({
                'director': bucket.key,
                'film_count': bucket.doc_count,
                FIELD_VOTE_AVERAGE: round(bucket.vote_average.value, 2)
            })
            if bucket.top_film.hits.hits:
                top_film = bucket.top_film.hits.hits[0]._source
                agg_result[-1]['top_film'] = {
                    'title': top_film['title'],
                    FIELD_VOTE_AVERAGE: top_film[FIELD_VOTE_AVERAGE]
                }
        return Response(agg_result)
    
    @action(detail=True, methods=['get'])
    def crew_analysis(self, request, id):
        """
        Provides an analysis of the crew for a specific film, including the count of crew members by department and job.
        """
        search = search_index(INDEX_NAME)

        search = search.query(Q('term', _id=id))
        search.aggs.bucket('films', 'terms', field = '_id') \
            .bucket('crew', 'nested', path = 'crew') \
            .bucket('departments', 'terms', field = 'crew.department') \
            .bucket('jobs', 'terms', field = 'crew.job')

        response = search.execute()
        if response.hits.total.value == 0:
            return Response({"error": "Film not found"}, status=status.HTTP_404_NOT_FOUND)
        agg_result = []
        for department_bucket in response.aggregations.films.buckets[0].crew.departments.buckets:
            department_result = {
                'departments': department_bucket.key,
                'crew_count': department_bucket.doc_count,
            }
            if department_bucket.jobs:
                department_result['jobs'] = []
                for job_bucket in department_bucket.jobs.buckets:
                    department_result['jobs'].append({
                        'job': job_bucket.key,
                        'job_count': job_bucket.doc_count
                    })
            agg_result.append(department_result)
                    
        return Response(agg_result)
    
    @action(detail=False, methods=['get'])
    def analysis(self, request):
        """
        Offers a yearly analysis of the number of films released, presented as a histogram.
        """
        search = search_index(INDEX_NAME)

        search.aggs.bucket('films_per_year', 'date_histogram', field = 'release_date', interval = 'year', format = 'yyyy', min_doc_count = 1)

        response = search.execute()
        agg_result = []
        for bucket in response.aggregations.films_per_year.buckets:
            agg_result.append({
                'year': bucket.key_as_string,
                'film_count': bucket.doc_count,
            })

        return Response(agg_result)

class SearchFilmAPIView(APIView):
    def get(self, request):
        """
        Allows searching for films based on title, genres, cast, and director, with pagination support.
        """
        search = search_index(INDEX_NAME)

        params = request.GET
        title = params.get('title', '')
        genres = params.get('genres', '')
        cast = params.get('cast', '')
        director = params.get('director', '')

        filters = []

        if title:
            filters.append(Q('multi_match', query=title, fields=['title^3', 'description']))
        if genres:
            genres = genres.split(',')
            filter_by_genre = [Q('term', genres=genre.strip()) for genre in genres]
            
            filters.append(
                Q(
                    'bool',
                    should = filter_by_genre,
                    minimum_should_match = 1
                )
            )
        if cast:
            filters.append(Q('match', cast = cast))
        if director:
            filters.append(Q('match', director = director))
        
        q = Q('bool',must = filters)
        search = search.query(q)

        page = int(params.get('page', 1))
        per_page = int(params.get('per_page', 10))
        search = search[(page - 1) * per_page:page * per_page]

        response = search.execute()

        serializer = serializers.FilmSerializer(response, many = True)
        return Response(serializer.data)