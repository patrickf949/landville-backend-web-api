release: python manage.py migrate

web: daphne -b 0.0.0.0 -p $PORT atterville.asgi:application
worker: celery -A atterville worker -l info
