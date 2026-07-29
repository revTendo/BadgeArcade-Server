import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SHOPDECK_SECRET_KEY", "django-insecure-1o&xlvoqsao=6i#h0kg6)n8xnte8%x7#ll7n4ky8ppgbo!=0bu")

DEBUG = os.environ.get("SHOPDECK_DEBUG", "1").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    'admin_interface',
    'colorfield',
    'shopdeckdb.apps.ShopdeckdbConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'shopdeckdb.middleware.ShopMiddleware',
    'shopdeckdb.middleware.DebugBodyMiddleware',
]

ROOT_URLCONF = 'shopdeck.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'webtemplates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'shopdeck.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get("MYSQL_DATABASE", "eshop"),
        'USER': os.environ.get("MYSQL_USER", "root"),
        'PASSWORD': os.environ.get("MYSQL_PASSWORD", ""),
        'HOST': os.environ.get("MYSQL_HOST", "127.0.0.1"),
        'PORT': os.environ.get("MYSQL_PORT", "3306"),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

_mysql_socket = os.environ.get("MYSQL_SOCKET")
if _mysql_socket:
    DATABASES['default']['HOST'] = ""
    DATABASES['default']['PORT'] = ""
    DATABASES['default']['OPTIONS']['unix_socket'] = _mysql_socket

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.environ.get("SHOPDECK_STATIC_ROOT", str(BASE_DIR / "_static"))
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
WHITENOISE_USE_FINDERS = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SOAP_URL = os.environ.get("SHOPDECK_SOAP_URL", "ecs.c.shop.revtendo.com")
METADATA_API_URL = os.environ.get("SHOPDECK_METADATA_URL", "ninja.ctr.shop.revtendo.com")

TOS_ESHOP = "revTendo eShop!"

MAINTENANCE_MSG = "Maintenance message."

IN_MAINTENANCE = False

WEBUI_NAME = os.environ.get("SHOPDECK_WEBUI_NAME", "revShop")

SESSION_COOKIE_NAME = "JSESSIONID"

AUTH_USER_MODEL = "shopdeckdb.User"

INSTALLED_APPS = INSTALLED_APPS + ['accountsdb.apps.AccountsdbConfig']
DATABASES['accounts'] = {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': os.environ.get("ACCOUNTS_MYSQL_DATABASE", "revtendoid"),
    'USER': os.environ.get("ACCOUNTS_MYSQL_USER", "revtendoaccounts"),
    'PASSWORD': os.environ.get("ACCOUNTS_MYSQL_PASSWORD", ""),
    'HOST': '', 'PORT': '',
    'OPTIONS': {'charset': 'utf8mb4', 'unix_socket': os.environ.get("ACCOUNTS_MYSQL_SOCKET", "/var/run/mysqld/mysqld.sock")},
}
DATABASE_ROUTERS = ['accountsdb.routers.AccountsRouter']
