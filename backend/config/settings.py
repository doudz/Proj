"""
Django settings for the GanttFlow project management platform.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "channels",
    "drf_spectacular",
    # local apps
    "apps.accounts",
    "apps.workspaces",
    "apps.projects",
    "apps.tasks",
    "apps.chat",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "ganttflow"),
        "USER": os.environ.get("POSTGRES_USER", "ganttflow"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "ganttflow"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "Europe/Paris")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# REST framework / JWT
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "GanttFlow API",
    "DESCRIPTION": "API de gestion de projet libre et open source (Kanban, Gantt, Chat)",
    "VERSION": "1.0.0",
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",") if o.strip()]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",") if o.strip()]

# ---------------------------------------------------------------------------
# Channels / Redis (WebSocket chat + real time notifications)
# ---------------------------------------------------------------------------
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, int(REDIS_PORT))],
        },
    },
}

# ---------------------------------------------------------------------------
# E-mail (used for "task available" notifications when a strict dependency
# is completed). Defaults to printing e-mails to the console in DEBUG so
# nothing needs to be configured for local development.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "GanttFlow <noreply@ganttflow.local>")

# Base URL of the frontend, used to build links inside notification e-mails.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost")

LOGIN_URL = "/admin/login/"

# ---------------------------------------------------------------------------
# Authentification LDAP / Active Directory (optionnelle, desactivee par
# defaut). Les comptes syncronises localement (ex: super-utilisateur cree par
# entrypoint.sh) continuent de s'authentifier via ModelBackend en priorite ;
# LDAP prend le relais pour toute autre adresse e-mail.
# ---------------------------------------------------------------------------
LDAP_ENABLED = os.environ.get("LDAP_ENABLED", "false").lower() == "true"

AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

if LDAP_ENABLED:
    import ldap
    from django_auth_ldap.config import GroupOfNamesType, LDAPSearch

    AUTH_LDAP_SERVER_URI = os.environ.get("LDAP_SERVER_URI", "ldap://ldap.example.com")
    AUTH_LDAP_BIND_DN = os.environ.get("LDAP_BIND_DN", "")
    AUTH_LDAP_BIND_PASSWORD = os.environ.get("LDAP_BIND_PASSWORD", "")

    # Recherche l'utilisateur par son e-mail (meme champ que le formulaire de
    # connexion) : %(user)s recoit la valeur passee a authenticate().
    AUTH_LDAP_USER_SEARCH = LDAPSearch(
        os.environ.get("LDAP_USER_SEARCH_BASE", "ou=users,dc=example,dc=com"),
        ldap.SCOPE_SUBTREE,
        os.environ.get("LDAP_USER_SEARCH_FILTER", "(mail=%(user)s)"),
    )

    AUTH_LDAP_USER_ATTR_MAP = {
        "first_name": os.environ.get("LDAP_ATTR_FIRST_NAME", "givenName"),
        "last_name": os.environ.get("LDAP_ATTR_LAST_NAME", "sn"),
        "email": os.environ.get("LDAP_ATTR_EMAIL", "mail"),
    }

    # Recree/met a jour le compte Django local a chaque connexion, avec un
    # mot de passe local inutilisable (le mot de passe reste dans l'annuaire).
    AUTH_LDAP_ALWAYS_UPDATE_USER = True
    AUTH_LDAP_START_TLS = os.environ.get("LDAP_START_TLS", "false").lower() == "true"
    AUTH_LDAP_CONNECTION_OPTIONS = {ldap.OPT_REFERRALS: 0}

    # Restreint la connexion aux membres d'un groupe LDAP donne (optionnel).
    _ldap_require_group = os.environ.get("LDAP_REQUIRE_GROUP_DN", "").strip()
    if _ldap_require_group:
        AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
            os.environ.get("LDAP_GROUP_SEARCH_BASE", "ou=groups,dc=example,dc=com"),
            ldap.SCOPE_SUBTREE,
            "(objectClass=groupOfNames)",
        )
        AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()
        AUTH_LDAP_REQUIRE_GROUP = _ldap_require_group

    AUTHENTICATION_BACKENDS.append("apps.accounts.ldap_backend.EmailLDAPBackend")
