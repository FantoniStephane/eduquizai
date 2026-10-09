from django.core.management.base import BaseCommand

from quiz.mongo import get_db
from quiz.schema import NOM_COLLECTION, initialiser_collection


class Command(BaseCommand):
    """Prépare la collection « quiz » : règle de validation et index."""

    help = "Crée ou met à jour la collection quiz de MongoDB (validation, index)."

    def handle(self, *args, **options):
        """Lance l'initialisation (peut être relancée sans risque)."""
        initialiser_collection(get_db())
        self.stdout.write(self.style.SUCCESS(f"Collection « {NOM_COLLECTION} » prête."))
