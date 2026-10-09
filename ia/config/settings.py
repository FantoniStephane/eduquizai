"""Réglages du microservice IA d'EduQuizAI.

Le microservice ne sert qu'à générer des quiz : pas de pages HTML, pas de
session, pas d'administration. Il n'est joignable que par l'application
web, sur le réseau interne de Docker (aucun port publié).
"""

from pathlib import Path

from decouple import Choices, Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("IA_SECRET_KEY")
DEBUG = config("IA_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("IA_ALLOWED_HOSTS", default="ia,localhost,127.0.0.1", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "generation",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# Pas de base de données pour l'instant : l'authentification de l'API
# (tâche 28) précisera ce besoin.
DATABASES = {}

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

# Fournisseur d'IA : « ollama » (modèle local, par défaut : les leçons ne
# quittent pas l'infrastructure) ou « mistral » (API externe, plus rapide)
IA_FOURNISSEUR = config(
    "IA_FOURNISSEUR", default="ollama", cast=Choices(["ollama", "mistral"])
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
