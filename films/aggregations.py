from elasticsearch_dsl import A

def build_top_film_agg():
    return A('top_hits', size = 1, sort = [{'vote_average': 'desc'}], _source = {'includes': ['title', 'vote_average']})

def build_popular_film_agg():
    return A('top_hits', size = 1, sort = [{'vote_count': 'desc'}], _source = {'includes': ['title', 'vote_count']})