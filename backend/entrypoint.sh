#!/bin/sh
set -e

echo "Attente de la base de donnees PostgreSQL (${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432})..."
python - <<'PYEOF'
import os
import socket
import time

host = os.environ.get("POSTGRES_HOST", "db")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
for _ in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit("Impossible de joindre PostgreSQL")
PYEOF

echo "Application des migrations..."
python manage.py migrate --noinput

echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "Verification du compte super-utilisateur..."
  python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
email = '$DJANGO_SUPERUSER_EMAIL'
if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password='$DJANGO_SUPERUSER_PASSWORD', first_name='Admin', last_name='')
"
fi

echo "Demarrage du serveur ASGI (Daphne, HTTP + WebSocket)..."
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
