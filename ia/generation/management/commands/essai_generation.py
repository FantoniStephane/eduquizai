import time

from django.conf import settings
from django.core.management.base import BaseCommand

from generation.erreurs import ErreurIAError
from generation.service import FOURNISSEURS, generer_quiz
from generation.validation import (
    DIFFICULTES,
    TYPES_QUESTION,
    ParametresInvalidesError,
    ReponseInvalideError,
)

LECON_EXEMPLE = """## La Révolution française

La Révolution française (1789-1799) est une période de bouleversements \
politiques et sociaux en France.

### Les causes
- une crise financière : le royaume est endetté ;
- des inégalités entre les trois ordres (clergé, noblesse, tiers état) ;
- la diffusion des idées des Lumières.

### Les grandes étapes
- 5 mai 1789 : ouverture des états généraux à Versailles ;
- 14 juillet 1789 : le peuple de Paris prend la Bastille ;
- 26 août 1789 : Déclaration des droits de l'homme et du citoyen ;
- 21 septembre 1792 : proclamation de la République.
"""


class Command(BaseCommand):
    """Génère un quiz sur une leçon d'exemple et mesure le temps de réponse."""

    help = "Essai réel de génération avec Ollama (affiche le quiz et la durée)."

    def add_arguments(self, parser):
        """Paramètres de la génération (mêmes limites que l'écran 7)."""
        parser.add_argument("--nombre", type=int, default=5)
        parser.add_argument("--difficulte", choices=DIFFICULTES, default="moyen")
        parser.add_argument(
            "--types", nargs="+", choices=TYPES_QUESTION, default=list(TYPES_QUESTION)
        )
        parser.add_argument("--fournisseur", choices=sorted(FOURNISSEURS))
        parser.add_argument(
            "--modele", help="Modèle à utiliser (par défaut : réglages)"
        )

    def handle(self, *args, **options):
        """Lance la génération et affiche le résultat."""
        fournisseur = options["fournisseur"] or settings.IA_FOURNISSEUR
        modele = options["modele"] or settings.OLLAMA["MODELE"]
        if fournisseur == "mistral":
            modele = options["modele"] or settings.MISTRAL["MODELE"]
        self.stdout.write(f"Fournisseur : {fournisseur} — modèle : {modele}")
        debut = time.perf_counter()
        try:
            questions = generer_quiz(
                LECON_EXEMPLE,
                difficulte=options["difficulte"],
                types=options["types"],
                nombre=options["nombre"],
                fournisseur=fournisseur,
                modele=modele,
            )
        except (ErreurIAError, ParametresInvalidesError, ReponseInvalideError) as exc:
            self.stderr.write(self.style.ERROR(f"Échec : {exc}"))
            return
        duree = time.perf_counter() - debut
        for numero, question in enumerate(questions, start=1):
            self.stdout.write(
                f"\n{numero}. [{question['type_question']}] {question['texte']}"
            )
            for choix in question["choix"]:
                marque = "x" if choix["est_correct"] else " "
                self.stdout.write(f"   [{marque}] {choix['texte']}")
            if question["reponse_attendue"]:
                self.stdout.write(
                    f"   Réponse attendue : {question['reponse_attendue']}"
                )
            self.stdout.write(f"   Explication : {question['explication']}")
        self.stdout.write(
            self.style.SUCCESS(f"\n{len(questions)} questions en {duree:.1f} s")
        )
