from config.elasticsearch_config import create_elasticsearch_connection
from elasticsearch_dsl import Document, Date, Integer, Keyword, Text, connections, Nested, Short, Float

es = create_elasticsearch_connection()
connections.add_connection("default", es)

class FilmDocument(Document):
    title = Text(
        fields = {
            'keyword': Keyword()
        }
    )
    runtime = Short()
    genres = Keyword()
    description = Text()
    crew = Nested(properties = {
        'name': Text(
            fields = {
                'keyword': Keyword()
            }
        ),
        'department': Keyword(),
        'job': Keyword()
    })
    director = Text(
        fields = {
            'keyword': Keyword()
        }
    )
    cast = Text(
        fields = {
            'keyword': Keyword()
        }
    )
    release_date = Date()
    status = Keyword()
    original_language = Keyword()
    vote_average = Float()
    vote_count = Integer()

    class Index:
        name = 'films'
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        }