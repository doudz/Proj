#!/bin/sh
set -e

echo "Attente de la base de donnees PostgreSQL (${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432})..."
python - <<'PYEOF'
import os
import sys
import time

import psycopg2

params = dict(
    host=os.environ.get("POSTGRES_HOST", "db"),
    port=os.environ.get("POSTGRES_PORT", "5432"),
    dbname=os.environ.get("POSTGRES_DB", "ganttflow"),
    user=os.environ.get("POSTGRES_USER", "ganttflow"),
    password=os.environ.get("POSTGRES_PASSWORD", "ganttflow"),
    connect_timeout=3,
)

last_error = None
for attempt in range(1, 61):
    try:
        conn = psycopg2.connect(**params)
        conn.close()
        break
    except psycopg2.OperationalError as exc:
        last_error = exc
        # Still starting up (connection refused) - keep waiting quietly.
        # Anything else (bad password, unknown database...) is a real
        # configuration problem: surface it immediately instead of
        # retrying blindly for a full minute.
        message = str(exc)
        if "could not connect to server" not in message and "Connection refused" not in message:
            print(f"Erreur de connexion PostgreSQL : {message.strip()}", file=sys.stderr)
            sys.exit(1)
        time.sleep(1)
else:
    print(f"Impossible de joindre PostgreSQL apres 60s : {last_error}", file=sys.stderr)
    sys.exit(1)
PYEOF

echo "Application des migrations..."
python manage.py migrate --noinput

echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "Synchronisation du compte super-utilisateur..."
  # Read email/password from the environment at runtime (never interpolated into
  # the Python source) and always (re)apply them: this keeps the account in sync
  # with the current .env on every restart, instead of only setting it correctly
  # the very first time the container ever ran with DJANGO_SUPERUSER_* set.
  python manage.py shell -c "
import os
from django.contrib.auth import get_user_model

User = get_user_model()
email = os.environ['DJANGO_SUPERUSER_EMAIL']
password = os.environ['DJANGO_SUPERUSER_PASSWORD']

user, created = User.objects.get_or_create(email=email, defaults={'first_name': 'Admin', 'last_name': ''})
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.set_password(password)
user.save()
print('Super-utilisateur cree.' if created else 'Super-utilisateur existant : identifiants synchronises avec .env.')
"
fi

echo "Demarrage du serveur ASGI (Daphne, HTTP + WebSocket)..."
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
