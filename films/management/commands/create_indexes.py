from django.core.management.base import BaseCommand
from films.documents import FilmDocument

class Command(BaseCommand):
    help = 'Create Elasticsearch indexes'

    def handle(self, *args, **kwargs):
        FilmDocument.init()
        self.stdout.write(self.style.SUCCESS('Indexes created successfully!'))