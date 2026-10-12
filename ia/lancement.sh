#!/bin/sh
# Démarrage du microservice IA : Gunicorn en production, serveur de
# développement de Django sinon.
set -e

if [ "$DJANGO_PRODUCTION" = "True" ]; then
    # Délai de 130 s : deux tentatives de génération au plus
    exec gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 2 \
        --timeout 130 --access-logfile -
fi

exec python manage.py runserver 0.0.0.0:8000
