"""Réglages du microservice IA d'EduQuizAI.

Le microservice ne sert qu'à générer des quiz : pas de pages HTML, pas de
session, pas d'administration. Il n'est joignable que par l'application
web, sur le réseau interne de Docker (aucun port publié).
"""

from datetime import timedelta
from pathlib import Path

from decouple import Choices, Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("IA_SECRET_KEY")
DEBUG = config("IA_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("IA_ALLOWED_HOSTS", default="ia,localhost,127.0.0.1", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "generation",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

# Lanceur de tests : journaux masqués pendant les tests
TEST_RUNNER = "config.test_runner.IaTestRunner"
WSGI_APPLICATION = "config.wsgi.application"

# Pas de base de données : le jeton JWT suffit à identifier l'appelant
# (voir SIMPLE_JWT), aucun utilisateur n'est enregistré dans ce service.
DATABASES = {}

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

# Fournisseur d'IA : « mistral » (API externe, par défaut : rapide et fiable,
# serveur de production sans carte graphique) ou « ollama » (modèle local :
# développement, fonctionnement hors ligne, leçons gardées sur la machine)
IA_FOURNISSEUR = config(
    "IA_FOURNISSEUR", default="mistral", cast=Choices(["ollama", "mistral"])
)

# Modèle de langage local (conteneur « ollama »)
OLLAMA = {
    "URL": config("OLLAMA_URL", default="http://127.0.0.1:11434"),
    "MODELE": config("OLLAMA_MODELE", default="llama3.2:3b"),
    # Délai maximum d'une génération, en secondes
    "DELAI": config("OLLAMA_DELAI", default=60, cast=int),
}

# API de Mistral AI (la clé est un secret : uniquement dans le fichier .env)
MISTRAL = {
    "URL": config("MISTRAL_URL", default="https://api.mistral.ai"),
    "CLE": config("MISTRAL_API_KEY", default=""),
    "MODELE": config("MISTRAL_MODELE", default="ministral-3b-2512"),
    "DELAI": config("MISTRAL_DELAI", default=30, cast=int),
}

# API REST : toutes les routes exigent un jeton JWT valide, rien n'est public.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # « Stateless » : lit l'identifiant dans le jeton, sans base de données
        "rest_framework_simplejwt.authentication.JWTStatelessUserAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
}

# Jetons JWT : signés par l'application web avec un secret partagé (dans le
# fichier .env, jamais dans Git), de courte durée ; émetteur et destinataire
# sont vérifiés pour refuser un jeton fabriqué pour un autre usage.
SIMPLE_JWT = {
    "SIGNING_KEY": config("IA_JWT_SECRET"),
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ISSUER": "eduquizai-web",
    "AUDIENCE": "eduquizai-ia",
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=2),
}
