# GanttFlow

**GanttFlow** est un outil de gestion de projet libre et open source (multi-utilisateur, auto-hebergeable), centre sur la planification de projet : tableau Kanban, **vue Gantt interactive** (glisser-deposer, dependances, jalons), liste, calendrier, et **chat/commentaires en temps reel** par tache.

- **Backend** : Python / Django + Django REST Framework + Django Channels (WebSocket) + PostgreSQL + Redis
- **Frontend** : Vue 3 + Vuetify 3 + Pinia + Vite
- **Deploiement** : Docker Compose, pret pour un serveur Linux

## Fonctionnalites

- Authentification par e-mail (JWT), inscription / connexion multi-utilisateur
- **Espaces de travail** (workspaces) avec roles (proprietaire, admin, membre, invite) et invitations
- **Projets** avec colonnes Kanban personnalisables, etiquettes (labels), membres
- **Taches** : dates de debut/echeance, avancement (%), priorite, sous-taches, pieces jointes, assignation multi-utilisateurs
- **Contacts externes** : assignez des taches a des personnes/sous-traitants sans compte GanttFlow (travail externalise) - notifies par e-mail uniquement (voir ci-dessous)
- **Dependances entre taches** (Fin->Debut, Debut->Debut, Fin->Fin, Debut->Fin), avec une option **bloquante** par dependance : la tache suivante ne peut pas etre demarree tant que la precedente n'est pas a 100% (voir ci-dessous)
- **Ligne de base** (baseline) : figez le planning de reference et comparez-le au reel (dates de debut/fin reelles, libres par rapport aux dates planifiees, ecart en jours)
- **Vue Gantt** (par projet) : zoom jour / semaine / mois, glisser-deposer pour replanifier, redimensionnement des barres, fleches de dependances, jalons, ligne "aujourd'hui", comparaison visuelle ligne de base / reel
- **Vue multi-projets** (portfolio) : toutes les taches d'un espace de travail sur une seule frise, pour reperer les goulots d'etranglement (voir ci-dessous)
- **Vue Kanban** : glisser-deposer entre colonnes
- **Vue Liste** et **Vue Calendrier**
- **Chat par tache** en temps reel (WebSocket) avec indicateur de saisie
- **Notifications en temps reel** (assignation de tache, tache disponible) + **e-mail** lorsqu'une tache bloquee par une dependance devient disponible
- Journal d'activite par tache

### Dependances bloquantes et notification "tache disponible"

Chaque dependance entre deux taches peut etre marquee comme **bloquante** (case a cocher lors de sa creation, ou icone cadenas sur la dependance existante). Quand elle l'est :

- La tache suivante ne peut pas etre demarree (bouton "Demarrer aujourd'hui" desactive, action API `/tasks/{id}/start/` refusee) tant que la tache precedente n'est pas a 100% d'avancement.
- Des qu'une tache precedente passe a 100%, chaque tache suivante bloquee par elle est reevaluee : si elle est desormais debloquee (toutes ses dependances bloquantes sont terminees) et qu'elle est toujours a l'etat initial ("a commencer", c'est-a-dire 0% et sans date de debut reelle), ses assignes recoivent une notification en temps reel **et un e-mail** les informant que la tache est disponible.

### Vue multi-projets (portfolio) et detection de goulots d'etranglement

Accessible depuis le menu lateral (« Vue multi-projets »), cette vue affiche sur une seule frise Gantt les taches de **plusieurs projets** d'un meme espace de travail, avec :

- des filtres par **projet**, par **assigne** et par **categorie** (etiquette, agregee par nom entre projets) ;
- trois modes de regroupement : **par projet**, **par assigne** (pour reperer une personne surchargee sur plusieurs projets a la fois) et **par categorie** (pour verifier si toutes les taches d'une meme categorie se chevauchent ou sont bien etalees) ;
- une **detection automatique des conflits de charge** : des qu'une meme personne a deux taches aux dates qui se chevauchent (tous projets confondus), les deux sont marquees d'un icone d'alerte (avec une info-bulle indiquant la tache en conflit) et comptabilisees dans le bandeau d'alerte en haut de la vue ;
- un clic sur une barre ouvre directement la fiche de la tache dans son projet d'origine.

Cette vue est en lecture/replanification simple (glisser-deposer pour changer les dates) mais n'affiche pas les dependances, la ligne de base ni le detail complet d'une tache : ces informations restent consultables projet par projet, en cliquant sur la tache.

Cette option est desactivee par defaut sur chaque dependance : les dependances "informatives" (sans blocage) restent possibles pour simplement visualiser un enchainement sur le Gantt sans contraindre le demarrage.

### Contacts externes (assigner une tache a un sous-traitant)

Par defaut, une tache ne peut etre assignee qu'a un membre de l'espace de travail (compte GanttFlow). Pour externaliser une tache (freelance, sous-traitant, client, etc. sans acces a l'outil), chaque espace de travail dispose d'un carnet de **contacts externes** :

- Gestion centralisee depuis le bouton « Contacts externes » de la page d'accueil de l'espace de travail (nom, e-mail, societe, telephone, notes).
- Depuis la fiche d'une tache, un champ **« Assignes externes »** (distinct du champ « Assignes » reserve aux membres) permet de choisir un ou plusieurs contacts existants, ou d'en creer un a la volee sans quitter la tache.
- Les contacts externes apparaissent partout ou les assignes sont affiches (carte Kanban, liste, vue multi-projets) avec un avatar a bordure en pointilles pour les distinguer des membres, et sont pris en compte dans la detection de conflits de charge de la vue multi-projets (un sous-traitant surbooke sur deux projets est detecte comme un membre interne).
- N'ayant pas de compte, un contact externe **ne recoit jamais de notification in-app** : il est prevenu **uniquement par e-mail**, a l'assignation d'une tache et lorsqu'une tache dont il depend (dependance bloquante) devient disponible - mêmes evenements que pour un membre interne, avec le meme reglage `EMAIL_*` (voir plus bas).

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

Un compte administrateur Django est cree automatiquement a partir de `DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_PASSWORD` (accessible sur `/admin/`), et re-synchronise a **chaque demarrage** du conteneur `backend` : si vous changez `DJANGO_SUPERUSER_PASSWORD` dans `.env`, le mot de passe du compte est mis a jour automatiquement au prochain `docker compose up`, sans etape manuelle. Les utilisateurs finaux s'inscrivent eux-memes depuis l'ecran "Creer un compte" de l'application.

### Mettre a jour

```bash
git pull
docker compose up -d --build
```

### Sauvegarder la base de donnees

```bash
docker compose exec db pg_dump -U ganttflow ganttflow > backup.sql
```

Pour restaurer : `cat backup.sql | docker compose exec -T db psql -U ganttflow ganttflow`.

### Consulter les journaux / diagnostiquer un probleme

```bash
docker compose ps                     # etat des conteneurs
docker compose logs -f backend        # API Django + WebSocket (Daphne)
docker compose logs -f frontend       # Nginx (build + service du frontend)
docker compose logs -f db redis       # base de donnees / cache
```

Si un conteneur boucle en erreur au demarrage, `docker compose logs backend` affiche generalement la cause (migration en echec, variable d'environnement manquante, base de donnees injoignable, etc.).

**Erreur frequente : "FATAL: password authentication failed"** — PostgreSQL n'applique `POSTGRES_PASSWORD` (et `POSTGRES_USER`/`POSTGRES_DB`) que lors de la toute premiere initialisation du volume `postgres_data`. Deux causes possibles :

- *Vous avez deja demarre le stack une fois* (meme brievement, avec un `.env` different ou les valeurs par defaut) : le volume garde l'ancien mot de passe et un `.env` modifie ensuite ne suffit plus a le changer.
- *Le gestionnaire de stack utilise n'interpole pas les `${VARIABLE}` du fichier compose* : certains outils (Dockhand, selon leur version) ne supportent pas la substitution `${POSTGRES_USER:-ganttflow}` de docker-compose et l'ignorent silencieusement, ce qui initialisait auparavant PostgreSQL avec les identifiants par defaut au lieu de ceux de `.env`. Depuis la version actuelle du `docker-compose.yml`, le service `db` lit `.env` directement via `env_file` (comme le service `backend`) et n'est plus concerne par ce probleme - mettez a jour votre checkout si vous rencontrez encore ce cas.

Dans les deux cas, la solution est la meme :

```bash
# Solution 1 (perte des donnees existantes) : reinitialiser le volume pour
# qu'il se reinitialise avec le mot de passe actuel de .env
docker compose down
docker volume rm proj_postgres_data   # ou le nom exact vu dans `docker volume ls`
docker compose up -d --build

# Solution 2 (conserver les donnees) : changer le mot de passe dans PostgreSQL
# lui-meme pour qu'il corresponde a POSTGRES_PASSWORD dans .env
docker compose exec db psql -U ganttflow -c "ALTER USER ganttflow WITH PASSWORD 'le-mot-de-passe-de-votre-.env';"
```

**Le port choisi via `HTTP_PORT` dans `.env` n'est pas pris en compte** — le mapping de port (`ports:`) doit obligatoirement etre resolu par l'outil qui lance le stack, il ne peut pas etre lu depuis l'interieur d'un conteneur comme les autres variables. Si votre gestionnaire de stack n'applique pas cette substitution, definissez le port directement dans son interface (mapping de port du service `frontend` vers le port 80 interne) plutot que via `HTTP_PORT`.

### Demarrage automatique au redemarrage du serveur

Les conteneurs sont deja configures avec `restart: unless-stopped` : ils redemarrent automatiquement si le demon Docker redemarre (par exemple apres un reboot du serveur), a condition que Docker lui-meme soit active au demarrage :

```bash
sudo systemctl enable docker
```

Aucune unite systemd supplementaire n'est necessaire pour l'application elle-meme.

### Mettre l'application derriere HTTPS (exemple avec Caddy)

Le conteneur `frontend` (Nginx) ecoute en clair sur le port defini par `HTTP_PORT` (80 par defaut). Pour exposer l'outil sur internet, placez un reverse proxy TLS devant, par exemple [Caddy](https://caddyserver.com/) qui obtient et renouvelle automatiquement un certificat Let's Encrypt.

1. Dans `.env`, faites pointer `HTTP_PORT` sur un port interne non expose publiquement (ex: `HTTP_PORT=8080`), et mettez a jour `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` et `FRONTEND_URL` avec votre nom de domaine en `https://`.
2. Installez Caddy sur le serveur (`apt install caddy` ou binaire officiel) et creez `/etc/caddy/Caddyfile` :

   ```caddyfile
   gantt.mondomaine.fr {
       reverse_proxy 127.0.0.1:8080

       # Necessaire pour le chat/les notifications en temps reel (WebSocket)
       @websockets {
           header Connection *Upgrade*
           header Upgrade    websocket
       }
       reverse_proxy @websockets 127.0.0.1:8080
   }
   ```

3. `sudo systemctl reload caddy`. Caddy gere seul l'obtention et le renouvellement du certificat TLS (DNS du domaine doit deja pointer vers le serveur).

Traefik ou Nginx + certbot fonctionnent tout aussi bien si vous les preferez ; le point important est de transferer l'en-tete `Upgrade: websocket` pour que le chat et les notifications temps reel continuent de fonctionner a travers le proxy.

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
- `EMAIL_*` / `DEFAULT_FROM_EMAIL` / `FRONTEND_URL` : configurez un serveur SMTP pour que les notifications "tache disponible" partent reellement par e-mail. Sans configuration (par defaut en `DJANGO_DEBUG=true`), les e-mails sont simplement affiches dans les logs du conteneur `backend`.
- Placez idealement l'application derriere un reverse proxy TLS (Caddy, Traefik, ou Nginx + certbot) devant le conteneur `frontend`.

## Limites connues / pistes d'evolution

- Pas encore de taches recurrentes, de vue "charge de travail" (workload) ni d'automatisations no-code (regles).
- Les e-mails sont envoyes pour : l'assignation d'un contact externe, et la notification "tache disponible" (dependance bloquante terminee) pour les membres comme pour les contacts externes. Les membres internes ne recoivent en revanche pas d'e-mail a l'assignation (notification in-app + temps reel uniquement). Les invitations et rappels d'echeance par e-mail restent a completer, de meme qu'une file d'attente (Celery) pour ne pas envoyer les e-mails de maniere synchrone sous forte charge.
- La creation de dependances se fait depuis le panneau de detail de la tache (pas encore par glisser-deposer directement sur le Gantt).

## Licence

Projet propose comme base libre et open source. Ajoutez le fichier de licence de votre choix (MIT, AGPL, etc.) selon vos besoins.
