from decouple import config
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search

def create_elasticsearch_connection():
    es = Elasticsearch(
        hosts=config('ELASTICSEARCH_HOST'),
        http_auth=(config('ELASTICSEARCH_USER'), config('ELASTICSEARCH_PASSWORD')),
    )
    return es

def search_index(index_name):
    connection = create_elasticsearch_connection()
    search = Search(using = connection, index = index_name)
    return search