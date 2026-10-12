#!/bin/sh
# Démarrage du conteneur web.
# - Production (DJANGO_PRODUCTION=True) : mise à jour de la base, table du
#   cache partagé, collection MongoDB, fichiers statiques, puis Gunicorn.
# - Développement : serveur de développement de Django (rechargement du code).
set -e

if [ "$DJANGO_PRODUCTION" = "True" ]; then
    python manage.py migrate --noinput
    python manage.py createcachetable
    python manage.py init_mongo
    python manage.py collectstatic --noinput
    # 3 processus ; délai de 150 s, plus long que l'attente d'une génération
    # (IA_DELAI, 130 s) ; journal des requêtes dans la sortie du conteneur
    exec gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 3 \
        --timeout 150 --access-logfile -
fi

exec python manage.py runserver 0.0.0.0:8000
