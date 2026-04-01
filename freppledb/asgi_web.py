import os
import django
from django.core.asgi import get_asgi_application

# Set the settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freppledb.settings")

# Fix for app registry issues
django.setup()

# Main ASGI application
application = get_asgi_application()
