from config.elasticsearch_config import create_elasticsearch_connection
from django.core.management.base import BaseCommand
from elasticsearch import helpers
from films.documents import FilmDocument
import json

class Command(BaseCommand):
    help = 'Populate Elasticsearch with data from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the JSON file with data')

    def handle(self, *args, **options):
        es = create_elasticsearch_connection()

        if not es.indices.exists(index="films"):
            FilmDocument.init()
            
        json_file_path = options['json_file']
        
        actions = []
        with open(json_file_path, 'r') as file:
            try:
                for line in file:
                    action = json.loads(line)
                    actions.append(action)
            except Exception as e:
                print(e)

        helpers.bulk(es, actions)
        self.stdout.write(self.style.SUCCESS('Successfully populated Elasticsearch with data'))