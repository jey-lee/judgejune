"""
WSGI config for judgejune project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'judgejune.settings')

try:
    application = get_wsgi_application()
except Exception as e:
    print("WSGI application error:")
    traceback.print_exc()
    sys.exit(1)
