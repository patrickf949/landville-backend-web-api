# Portable container for the LandVille backend (works on Fly.io, Koyeb,
# Render, Railway, or any Docker host). Render can also deploy natively
# via render.yaml — this Dockerfile is for hosts that want an image.
FROM python:3.12.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Dummy key just so collectstatic can import settings at build time;
# the real SECRET_KEY is injected at runtime by the host.
RUN SECRET_KEY=build-time-only python manage.py collectstatic --noinput

EXPOSE ${PORT}

# Migrate on boot, then serve ASGI (websockets + HTTP) via daphne.
CMD python manage.py migrate --noinput && \
    celery -A landville worker -l info & \
    daphne -b 0.0.0.0 -p ${PORT} landville.asgi:application
