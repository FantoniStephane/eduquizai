from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class Role(models.TextChoices):
    """Rôles possibles d'un utilisateur."""

    ENSEIGNANT = "enseignant", "Enseignant"
    ADMIN = "admin", "Administrateur"


class UtilisateurManager(BaseUserManager):
    """Crée les comptes : l'e-mail sert d'identifiant de connexion."""

    def create_user(self, email, password, **champs):
        """Crée et enregistre un utilisateur avec un mot de passe haché.

        Args:
            email: Adresse e-mail, utilisée comme identifiant de connexion.
            password: Mot de passe en clair, haché avant l'enregistrement.
            **champs: Autres champs du modèle (nom, prenom, role…).

        Returns:
            L'utilisateur créé.

        Raises:
            ValueError: Si l'adresse e-mail est vide.
        """
        if not email:
            raise ValueError("L'adresse e-mail est obligatoire.")
        utilisateur = self.model(email=self.normalize_email(email), **champs)
        utilisateur.set_password(password)  # mot de passe haché, jamais en clair
        utilisateur.save(using=self._db)
        return utilisateur

    def create_superuser(self, email, password, **champs):
        """Crée un administrateur (rôle « admin », tous les droits).

        Args:
            email: Adresse e-mail de l'administrateur.
            password: Mot de passe en clair, haché avant l'enregistrement.
            **champs: Autres champs du modèle (nom, prenom…).

        Returns:
            L'administrateur créé.
        """
        champs.setdefault("role", Role.ADMIN)
        champs.setdefault("is_superuser", True)
        return self.create_user(email, password, **champs)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    """Enseignant ou administrateur de la plateforme (entité UTILISATEUR du MCD)."""

    id = models.BigAutoField(primary_key=True, db_column="id_utilisateur")
    nom = models.CharField("nom", max_length=50)
    prenom = models.CharField("prénom", max_length=50)
    email = models.EmailField("adresse e-mail", max_length=100, unique=True)
    password = models.CharField(
        "mot de passe", max_length=255, db_column="mot_de_passe"
    )
    role = models.CharField(
        "rôle", max_length=20, choices=Role.choices, default=Role.ENSEIGNANT
    )
    is_active = models.BooleanField("actif", default=True, db_column="est_actif")
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    objects = UtilisateurManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ("nom", "prenom")

    class Meta:
        db_table = "utilisateur"
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=Role.values),
                name="utilisateur_role_valide",
            ),
        ]

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    def save(self, *args, **kwargs):
        """Aligne les droits d'administration sur le rôle avant l'enregistrement."""
        self.is_superuser = self.role == Role.ADMIN
        super().save(*args, **kwargs)

    @property
    def is_staff(self):
        """Seul l'administrateur accède à l'admin Django."""
        return self.role == Role.ADMIN
