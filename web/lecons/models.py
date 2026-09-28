from django.conf import settings
from django.db import models


class Matiere(models.TextChoices):
    """Matières proposées dans le formulaire de leçon (voir les maquettes)."""

    FRANCAIS = "francais", "Français"
    HISTOIRE = "histoire", "Histoire"
    MATHEMATIQUES = "mathematiques", "Mathématiques"
    SVT = "svt", "SVT"
    ANGLAIS = "anglais", "Anglais"


class Niveau(models.TextChoices):
    """Niveaux scolaires du collège."""

    SIXIEME = "6e", "6e"
    CINQUIEME = "5e", "5e"
    QUATRIEME = "4e", "4e"
    TROISIEME = "3e", "3e"


class Lecon(models.Model):
    """Leçon rédigée par un enseignant (entité LECON du MCD)."""

    id = models.BigAutoField(primary_key=True, db_column="id_lecon")
    titre = models.CharField(max_length=100)
    matiere = models.CharField(max_length=50, choices=Matiere.choices)
    niveau_scolaire = models.CharField(max_length=20, choices=Niveau.choices)
    contenu = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lecons",
        db_column="id_utilisateur",
    )

    class Meta:
        db_table = "lecon"
        ordering = ["-date_modification"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(matiere__in=Matiere.values),
                name="lecon_matiere_valide",
            ),
            models.CheckConstraint(
                condition=models.Q(niveau_scolaire__in=Niveau.values),
                name="lecon_niveau_valide",
            ),
        ]

    def __str__(self):
        return self.titre
