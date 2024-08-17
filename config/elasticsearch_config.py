from decouple import config
from elasticsearch import Elasticsearch

def create_elasticsearch_connection():
    es = Elasticsearch(
        hosts=config('ELASTICSEARCH_HOST'),
        http_auth=(config('ELASTICSEARCH_USER'), config('ELASTICSEARCH_PASSWORD')),
    )
    return es