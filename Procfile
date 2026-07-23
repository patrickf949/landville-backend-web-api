release: python manage.py migrate

web: daphne -b 0.0.0.0 -p $PORT landville.asgi:application
worker: celery -A landville worker -l info
