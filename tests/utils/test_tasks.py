from unittest.mock import patch
import time

from django.core.mail import EmailMultiAlternatives
from django.test import TestCase

from tests.factories.authentication_factory import UserFactory
from utils.tasks import send_email_notification


class TaskWorkerTest(TestCase):
    """
    Tests for background task execution via Django's task framework.
    """

    def setUp(self):
        self.user = UserFactory.create()
        self.email_body = {
            "subject": "Test Status",
            "recipient": [self.user.email + "m"],
            "text_body": "email/authentication/base_email.txt",
            "html_body": "email/authentication/base_email.html",
            "context": {
                'title': "Hey there,",
                'message': "test"
            }
        }

    @patch('django.core.mail.EmailMultiAlternatives.send')
    def test_handle_sending_email_direct(self, mock_email):
        """
        Test direct invocation of send_email_notification.
        """
        mock_email.return_value = True
        send_email_notification(self.email_body)
        self.assertTrue(mock_email.called)

    @patch('django.core.mail.EmailMultiAlternatives.send')
    def test_handle_sending_email_delay(self, mock_email):
        """
        Test background enqueue via .delay() method.
        """
        mock_email.return_value = True
        result = send_email_notification.delay(self.email_body)
        self.assertIsNotNone(result)

        # Allow worker thread a moment to finish execution
        time.sleep(0.3)
        self.assertTrue(mock_email.called)
