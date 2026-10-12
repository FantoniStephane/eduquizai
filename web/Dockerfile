FROM python:3.12-slim

# Pas de fichiers .pyc, logs affichés immédiatement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances d'abord : Docker garde cette étape en cache tant que requirements.txt ne change pas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Sécurité : l'application ne tourne pas en root. Elle n'a le droit d'écrire
# que dans le dossier des fichiers statiques (collectstatic en production)
RUN useradd --create-home appuser \
    && mkdir -p /app/staticfiles \
    && chown appuser /app/staticfiles
USER appuser

EXPOSE 8000
# Gunicorn en production, serveur de développement sinon (voir lancement.sh)
CMD ["sh", "lancement.sh"]
