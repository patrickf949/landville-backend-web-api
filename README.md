[![CircleCI](https://circleci.com/gh/attervilleng/atterville-backend-web-api.svg?style=svg&circle-token=0b67e7bdea3b38a5b4be3154613c500fb0ba12db)](https://circleci.com/gh/attervilleng/atterville-backend-web-api) [![Coverage Status](https://coveralls.io/repos/github/attervilleng/atterville-backend-web-api/badge.svg?branch=develop&t=8IKdIj)](https://coveralls.io/github/attervilleng/atterville-backend-web-api?branch=develop)
<a href="https://codeclimate.com/github/attervilleng/atterville-backend-web-api/maintainability"><img src="https://api.codeclimate.com/v1/badges/6ff3cfebdbf6655c3da0/maintainability" /></a>

# atterville-backend-web-api

Backend Repository for the Atterville Project

# Description

- Atterville is a platform that connects people to properties and places. Anyone can list a property - for rent, for sale, or land - with photos, amenities, and location details. Seekers search, filter, view listings on a map, and chat directly with owners. Atterville does not handle payments; it exists purely to connect.

> **Note:** internal module names and the `/atterville/adm/` admin URL retain the legacy name pending a separate internal rename.

## Local setup (quick start)

Create the local database and user (run in `psql` as a superuser):

```sql
CREATE USER atterville_admin WITH PASSWORD 'JI2kyz5ayMALhrKO4*GkACeF@0uY';
CREATE DATABASE atterville_local OWNER atterville_admin;
GRANT ALL PRIVILEGES ON DATABASE atterville_local TO atterville_admin;
ALTER USER atterville_admin CREATEDB;
\c atterville_local
GRANT ALL ON SCHEMA public TO atterville_admin;
```

Then export the environment (or put it in a gitignored `.env`):

```bash
export DB_NAME=atterville_local
export DB_USER=atterville_admin
export DB_PASSWORD='JI2kyz5ayMALhrKO4*GkACeF@0uY'
export DB_HOST=localhost
export DB_PORT=5432
export REDIS_URL=redis://localhost:6379   # required for chat + celery
```

Install, migrate, seed and run (ASGI server so websockets work):

```bash
pip install -r requirements.txt
python manage.py migrate
python load_fixtures.py            # amenity catalogue + demo listings
daphne -b 0.0.0.0 -p 8000 atterville.asgi:application
```

Without `REDIS_URL` the chat falls back to an in-memory channel layer (fine for a single dev process).

## Documentation

- List of endpoints exposed by the service

| Method    | Endpoint                                        | Description                                            |
| --------- | ----------------------------------------------- | ------------------------------------------------------ |
| POST      | /atterville/adm/                                  | log in Admin (legacy URL)                              |
| POST      | /api/v1/auth/register/                           | registers new users by email                           |
| GET       | /api/v1/auth/verify/                             | activates a users account                              |
| POST      | /api/v1/auth/login/                              | logs in a user by email                                |
| POST      | /api/v1/auth/google/                             | user signs in through google                           |
| POST      | /api/v1/auth/twitter/                            | user signs in through twitter                          |
| POST      | /api/v1/auth/facebook/                           | user signs in through facebook                         |
| POST      | /api/v1/auth/password-reset/                     | user gets a reset password link                        |
| PATCH     | /api/v1/auth/password-reset/                     | user resets password                                   |
| GET/PATCH | /api/v1/auth/profile/                            | get or edit the logged-in user's profile               |
| GET       | /api/v1/properties/                              | list/search published listings (rich filters)         |
| POST      | /api/v1/properties/                              | create a listing (any registered user)                |
| GET       | /api/v1/properties/amenities/                    | amenity catalogue for forms and filters                |
| GET       | /api/v1/properties/nearby-features/              | nearby-feature catalogue                               |
| GET       | /api/v1/properties/\<slug\>/                     | get a specific listing                                 |
| PATCH     | /api/v1/properties/\<slug\>/                     | update your listing                                    |
| DELETE    | /api/v1/properties/\<slug\>/                     | delete your listing                                    |
| PATCH     | /api/v1/properties/\<slug\>/status/              | mark your listing Available / Rented / Sold            |
| DELETE    | /api/v1/properties/\<slug\>/resource             | delete a cloudinary resource                           |
| GET       | /api/v1/properties/buyer-list/                   | get your saved properties                              |
| POST      | /api/v1/properties/buyer-list/\<slug\>/          | save a property                                        |
| DELETE    | /api/v1/properties/buyer-list/\<slug\>/          | remove a saved property                                |
| GET       | /api/v1/properties/trending/?city=City           | trending properties in a location                      |
| POST      | /api/v1/properties/enquiries/\<slug\>/create/    | post a property enquiry                                |
| GET       | /api/v1/properties/enquiries/all/                | get all your enquiries                                 |
| GET/PUT/DELETE | /api/v1/properties/enquiries/\<enquiry_id\>/ | manage one enquiry                                    |
| GET       | /api/v1/chat/conversations/                      | your chat inbox                                        |
| POST      | /api/v1/chat/conversations/start/\<slug\>/       | start (or reopen) a chat about a listing               |
| GET/POST  | /api/v1/chat/conversations/\<id\>/messages/      | chat history / send a message (REST fallback)          |
| POST      | /api/v1/chat/conversations/\<id\>/report/        | report a conversation                                  |
| POST      | /api/v1/chat/conversations/\<id\>/block/         | block a conversation                                   |
| WS        | /ws/chat/\<conversation_id\>/?token=\<jwt\>      | real-time text chat (Django Channels)                  |

> Payments, bank accounts and client-company endpoints were removed: Atterville is a pure connection platform.

## API Documentation

https://atterville-backend-web-api.herokuapp.com/

The heroku link redirects direclty to our documentation With these documentation, One can be able to test all endpoint as mentioned above in a browser

## Setup

- Step by step instructions on how to get the code setup locally. This may include:

  ### Description:

- *Celery* is a task queue with focus on real-time processing, while also supporting task scheduling.
- *Redis* is a message broker. This means it handles the queue of "messages" between Django and Celery.
- All two work together to make real-time magic.
- This module contains the Celery application instance for this project, we take configuration from Django settings and use autodiscover_tasks to find task modules inside all packages listed in INSTALLED_APPS.

      ### Installing requirements

  The settings file assumes that rabbitmq-server is running on localhost using the default ports.

### Dependencies

    - python3.7
    - python3
    - pip3
    - django 2.2.1
    - celery
    - redis

### Getting Started

- First clone the project to your local machine using `git clone https://github.com/attervilleng/atterville-backend-web-api.git`
- Create a virtual environment using the following command : `python3 -m venv /path/to/new/virtual/environment`
- Activate your virtual environment using `source (virtualenv name)/bin/activate`
- Create a new branch from the develop branch using the command `git checkout -b your_branch_name`
- Install project requirements using `pip install -r requirements.txt`
- To create a dot_env file `.env`, run the command `cp .env_sample .env` so that the `.env_sample` file can be copied to `.env`.
- Edit the `.env` file with your own credentials. Eg : database username, password ,etc
- Make sure you have `export REDIS_URL="redis://localhost:6379"` in your .env file.
  (this allows the celery to connect with redis.)
- Set your environement variable by running the following command `source .env`
- Create a Postgres database with the name you put in the `.env` file
- Run the command `python manage.py migrate` to create database tables
- Download Redis
  - Using Homebrew:  `$ brew install redis`
  - Start Redis server  `$ brew services start redis`
- Open & Test Redis:
  `$ redis-server`
- Run worker:
  `` $ celery -A yourproject worker -l info` `` \* example
  `$ celery -A atterville worker -l info`
- Run command `python manage.py runserver` to start the project

### Run The Service

- List of steps to run the service (e.g. docker commands)

### Microservices

- List out the microservices if any that this repo uses(This will include the payment service we shall be using)

## Testing

- To run tests without coverage run `python manage.py test`
- To run tests with coverage run `coverage run --source='authentication/,property/,transactions/,pages/,' manage.py test && coverage report`

## Contribute

- For contributions to this project, reach out

## Deployment

- This project has been depolyed on heroku:
  link(https://atterville-backend-web-api.herokuapp.com/)
