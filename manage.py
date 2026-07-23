#!/usr/bin/env python
import os
import sys

if __name__ == '__main__':
    # Load .env file manually if it exists
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    key = key.strip()
                    if key.startswith('export '):
                        key = key[7:]
                    val = val.strip().strip("'").strip('"')
                    os.environ.setdefault(key.strip(), val)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'landville.settings')
    try:
        from django.core.management import execute_from_command_line
        from django.conf import settings
        if 'test' in sys.argv:
            import logging
            logging.disable(logging.CRITICAL)
            settings.DEBUG = False
            settings.TEMPLATE_DEBUG = False
            # this setting reduce the time taken by our test by 6
            settings.PASSWORD_HASHERS = [
                'django.contrib.auth.hashers.MD5PasswordHasher',
            ]

    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
