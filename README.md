# GanttFlow

**GanttFlow** est une alternative libre et open source (multi-utilisateur, auto-hebergeable) a Monday.com et Asana, centree sur la planification de projet : tableau Kanban, **vue Gantt interactive** (glisser-deposer, dependances, jalons), liste, calendrier, et **chat/commentaires en temps reel** par tache.

- **Backend** : Python / Django + Django REST Framework + Django Channels (WebSocket) + PostgreSQL + Redis
- **Frontend** : Vue 3 + Vuetify 3 + Pinia + Vite
- **Deploiement** : Docker Compose, pret pour un serveur Linux

## Fonctionnalites

- Authentification par e-mail (JWT), inscription / connexion multi-utilisateur
- **Espaces de travail** (workspaces) avec roles (proprietaire, admin, membre, invite) et invitations
- **Projets** avec colonnes Kanban personnalisables, etiquettes (labels), membres
- **Taches** : dates de debut/echeance, avancement (%), priorite, sous-taches, pieces jointes, assignation multi-utilisateurs
- **Dependances entre taches** (Fin->Debut, Debut->Debut, Fin->Fin, Debut->Fin)
- **Vue Gantt** : zoom jour / semaine / mois, glisser-deposer pour replanifier, redimensionnement des barres, fleches de dependances, jalons, ligne "aujourd'hui"
- **Vue Kanban** : glisser-deposer entre colonnes
- **Vue Liste** et **Vue Calendrier**
- **Chat par tache** en temps reel (WebSocket) avec indicateur de saisie
- **Notifications en temps reel** (assignation de tache, etc.)
- Journal d'activite par tache

## Architecture

```
Proj/
├── backend/            # API Django REST + Channels (ASGI/Daphne)
│   ├── apps/
│   │   ├── accounts/       # Utilisateur custom (email), JWT
│   │   ├── workspaces/     # Espaces de travail, membres, invitations
│   │   ├── projects/       # Projets, colonnes Kanban, etiquettes
│   │   ├── tasks/          # Taches, dependances, commentaires, pieces jointes
│   │   ├── chat/           # Consumers WebSocket (chat + evenements temps reel)
│   │   └── notifications/  # Notifications utilisateur
│   └── config/          # Settings, urls, asgi/wsgi
├── frontend/            # Application Vue 3 / Vuetify 3 (Vite)
│   └── src/
│       ├── components/gantt/   # Composant Gantt (SVG + drag & drop)
│       ├── components/kanban/  # Tableau Kanban (vuedraggable)
│       ├── components/task/    # Detail de tache + chat
│       ├── components/calendar/
│       ├── stores/              # Pinia (auth, workspace, project, task, notification)
│       └── services/            # Client API (axios) + WebSocket
├── docker-compose.yml
└── nginx/ (reverse proxy embarque dans le conteneur frontend)
```

## Demarrage rapide (Docker, recommande pour un serveur Linux)

Pre-requis : [Docker](https://docs.docker.com/engine/install/) et [Docker Compose](https://docs.docker.com/compose/install/) installes sur votre serveur Linux.

```bash
git clone <votre-fork> ganttflow
cd ganttflow
cp .env.example .env
# Editez .env : changez DJANGO_SECRET_KEY, les mots de passe, et l'admin par defaut

docker compose up -d --build
```

L'application est alors disponible sur `http://<votre-serveur>` (port 80 par defaut, modifiable via `HTTP_PORT` dans `.env`).

Un compte administrateur Django est cree automatiquement au premier demarrage a partir de `DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_PASSWORD` (accessible sur `/admin/`). Les utilisateurs finaux s'inscrivent eux-memes depuis l'ecran "Creer un compte" de l'application.

### Mettre a jour

```bash
git pull
docker compose up -d --build
```

### Sauvegarder la base de donnees

```bash
docker compose exec db pg_dump -U ganttflow ganttflow > backup.sql
```

## Developpement local (sans Docker)

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Demarrer PostgreSQL et Redis localement (ou via docker: `docker compose up -d db redis`)
export POSTGRES_HOST=localhost REDIS_HOST=localhost DJANGO_DEBUG=true

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

Pour beneficier du WebSocket (chat/notifications) en developpement, lancez plutot le serveur ASGI :

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Le serveur de developpement Vite (`http://localhost:5173`) proxifie automatiquement `/api` et `/ws` vers `http://localhost:8000` (voir `vite.config.js`).

## Variables d'environnement principales

Voir `.env.example` pour la liste complete. Points d'attention en production :

- `DJANGO_SECRET_KEY` : obligatoire, generez une valeur aleatoire longue.
- `DJANGO_DEBUG=false` en production.
- `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` : doivent correspondre au(x) domaine(s) reel(s) utilise(s) pour acceder a l'application (ex: `https://gantt.mondomaine.fr`).
- Placez idealement l'application derriere un reverse proxy TLS (Caddy, Traefik, ou Nginx + certbot) devant le conteneur `frontend`.

## Limites connues / pistes d'evolution

- Pas encore de taches recurrentes, de vue "charge de travail" (workload) ni d'automatisations no-code (regles) comme Monday.com.
- Les emails transactionnels (invitations, rappels d'echeance) ne sont pas envoyes automatiquement — a completer avec un backend SMTP (`EMAIL_BACKEND`) et Celery pour les taches planifiees.
- La creation de dependances se fait depuis le panneau de detail de la tache (pas encore par glisser-deposer directement sur le Gantt).

## Licence

Projet propose comme base libre et open source. Ajoutez le fichier de licence de votre choix (MIT, AGPL, etc.) selon vos besoins.
