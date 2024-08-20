from django.urls import path
from . import views

film_list = views.FilmViewSet.as_view({
    'get': 'list'
})
top_films = views.FilmViewSet.as_view({
    'get': 'top_films'
})
genres = views.FilmViewSet.as_view({
    'get': 'genres'
})
directors = views.FilmViewSet.as_view({
    'get': 'directors'
})
analysis = views.FilmViewSet.as_view({
    'get': 'analysis'
})
crew_analysis = views.FilmViewSet.as_view({
    'get': 'crew_analysis'
})
urlpatterns = [
    path('films/', film_list, name='film-list'),
    path('top_films/', top_films, name='top-films'),
    path('films/genres/', genres, name='films-genre'),
    path('films/directors/', directors, name='films-director'),
    path('films/analysis/', analysis, name='films-analysis'),
    path('films/<int:id>/crew_analysis/', crew_analysis, name='films-crew'),
    path('search/', views.SearchFilmAPIView.as_view()),
]