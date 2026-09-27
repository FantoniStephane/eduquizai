from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class UtilisateurManager(BaseUserManager):
    """Crée les comptes : l'e-mail sert d'identifiant de connexion."""

    def create_user(self, email, password, **champs):
        if not email:
            raise ValueError("L'adresse e-mail est obligatoire.")
        utilisateur = self.model(email=self.normalize_email(email), **champs)
        utilisateur.set_password(password)  # mot de passe haché, jamais en clair
        utilisateur.save(using=self._db)
        return utilisateur

    def create_superuser(self, email, password, **champs):
        champs.setdefault("role", Utilisateur.Role.ADMIN)
        champs.setdefault("is_superuser", True)
        return self.create_user(email, password, **champs)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    """Enseignant ou administrateur de la plateforme (entité UTILISATEUR du MCD)."""

    class Role(models.TextChoices):
        ENSEIGNANT = "enseignant", "Enseignant"
        ADMIN = "admin", "Administrateur"

    id = models.BigAutoField(primary_key=True, db_column="id_utilisateur")
    nom = models.CharField(max_length=50)
    prenom = models.CharField(max_length=50)
    email = models.EmailField(max_length=100, unique=True)
    password = models.CharField(max_length=255, db_column="mot_de_passe")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ENSEIGNANT)
    is_active = models.BooleanField(default=True, db_column="est_actif")
    date_creation = models.DateTimeField(auto_now_add=True)

    objects = UtilisateurManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ("nom", "prenom")

    class Meta:
        db_table = "utilisateur"

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    @property
    def is_staff(self):
        """Seul l'administrateur accède à l'admin Django."""
        return self.role == self.Role.ADMIN
