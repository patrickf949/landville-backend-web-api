from django.test import TestCase
from django.urls import reverse
from rest_framework import authentication, exceptions
from datetime import datetime, timedelta
from faker import Factory
import jwt

from rest_framework import status
from rest_framework.test import APITestCase
from django.conf import settings

from authentication.models import User, PasswordResetToken
from tests.factories.authentication_factory import UserFactory, PasswordResetTokenFactory


class PasswordResetTokenTestBase(APITestCase):
    """Test the password reset feature """

    def setUp(self):
        self.faker = Factory.create()
        self.normal_user = UserFactory.create()
        self.reset_password_url = reverse('authentication:password-reset')
        self.change_password_url = self.reset_password_url + '?token/{}'
        self.expired_token_time = datetime.now() - timedelta(hours=1)
        self.token_expiry = datetime.now() + timedelta(hours=24)

        def safe_jwt_encode(payload):
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
            return token.decode('utf-8') if isinstance(token, bytes) else token

        self.reset_token = safe_jwt_encode({
            'email': self.normal_user.email,
            'exp': int(self.token_expiry.strftime('%s'))
        })
        self.token_object = PasswordResetTokenFactory.create(
            token=self.reset_token)

        self.expired_token = safe_jwt_encode({
            'email': self.normal_user.email,
            'exp': int(self.expired_token_time.strftime('%s'))
        })
        self.token_object2 = PasswordResetTokenFactory.create(
            token=self.expired_token)

        self.non_existent_user_token = safe_jwt_encode({
            'email': self.faker.email(),
            'exp': int(self.token_expiry.strftime('%s'))
        })
        self.fake_token_object = PasswordResetTokenFactory.create(
            token=self.non_existent_user_token)

        self.fake_token = 'invalid_format_token'
        self.fake_token_object2 = PasswordResetTokenFactory.create(
            token=self.fake_token)

        self.valid_user_data = {
            'email': self.normal_user.email
        }

        self.invalid_user_data = {
            'email': self.faker.email()
        }

        self.password1 = self.faker.text()[:40]
        self.password2 = self.faker.text()[:40]

        self.valid_passwords = {
            'password': self.password1,
            'confirm_password': self.password1
        }

        self.unmatching_passwords = {
            'password': self.password1,
            'confirm_password': self.password2
        }

        self.weak_password = {
            'password': 'password',
            'confirm_password': 'password',
        }
