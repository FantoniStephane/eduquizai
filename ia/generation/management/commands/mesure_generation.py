import statistics
import time

from django.core.management.base import BaseCommand

from generation.erreurs import ErreurIAError
from generation.management.commands.essai_generation import LECON_EXEMPLE
from generation.service import FOURNISSEURS, generer_quiz
from generation.validation import ReponseInvalideError

TYPES = ["qcm", "vrai_faux", "ouverte"]


class Command(BaseCommand):
    """Compare le temps de génération et le taux de réussite de plusieurs modèles.

    Pour chaque modèle : un premier essai « à froid » (le modèle peut devoir
    être chargé en mémoire), puis plusieurs essais « à chaud ». Les résultats
    servent à choisir le modèle et sont reportés dans le dossier projet.
    """

    help = "Mesure le temps de génération d'un quiz pour un ou plusieurs modèles."

    def add_arguments(self, parser):
        """Modèles à comparer, nombre d'essais et taille du quiz."""
        parser.add_argument("modeles", nargs="+", help="Modèles à comparer")
        parser.add_argument("--fournisseur", choices=sorted(FOURNISSEURS))
        parser.add_argument("--essais", type=int, default=3, help="Essais à chaud")
        parser.add_argument("--nombre", type=int, default=5)

    def essai(self, modele, options):
        """Lance une génération ; retourne (durée en secondes, résultat)."""
        debut = time.perf_counter()
        try:
            generer_quiz(
                LECON_EXEMPLE,
                difficulte="moyen",
                types=TYPES,
                nombre=options["nombre"],
                fournisseur=options["fournisseur"],
                modele=modele,
            )
            resultat = "valide"
        except ReponseInvalideError as exc:
            resultat = f"invalide : {exc}"
        except ErreurIAError as exc:
            resultat = f"erreur : {exc}"
        return time.perf_counter() - debut, resultat

    def handle(self, *args, **options):
        """Affiche un tableau : une ligne par modèle."""
        self.stdout.write(
            f"Quiz de {options['nombre']} questions, "
            f"1 essai à froid + {options['essais']} à chaud par modèle\n"
        )
        self.stdout.write(
            "| Modèle | À froid (s) | À chaud min / moy / max (s) | Valides |"
        )
        self.stdout.write("|---|---|---|---|")
        for modele in options["modeles"]:
            froid, resultat_froid = self.essai(modele, options)
            mesures = [self.essai(modele, options) for _ in range(options["essais"])]
            chauds = [duree for duree, _ in mesures]
            valides = [resultat_froid, *(r for _, r in mesures)].count("valide")
            erreurs = {r for _, r in [(froid, resultat_froid), *mesures]}
            erreurs.discard("valide")
            chaud = (
                f"{min(chauds):.1f} / {statistics.mean(chauds):.1f} / {max(chauds):.1f}"
                if chauds
                else "—"
            )
            self.stdout.write(
                f"| {modele} | {froid:.1f} | {chaud} | "
                f"{valides}/{options['essais'] + 1} |"
            )
            for erreur in sorted(erreurs):
                self.stdout.write(f"  {modele} : {erreur}")
