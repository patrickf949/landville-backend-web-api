from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status


class SecurityAndProtectionTests(TestCase):
    """
    Tests for origin protection, scanner blocking, and security headers.
    """

    def setUp(self):
        self.client = APIClient()

    def test_allowed_origin_passes(self):
        """Requests from landville.vercel.app should be allowed."""
        response = self.client.get(
            '/api/v1/properties/amenities/',
            HTTP_ORIGIN='https://landville.vercel.app'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['X-Frame-Options'], 'DENY')

    def test_atterville_origin_passes(self):
        """Requests from atterville.vercel.app should be allowed."""
        response = self.client.get(
            '/api/v1/properties/amenities/',
            HTTP_ORIGIN='https://atterville.vercel.app'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(DEBUG=False)
    def test_unauthorized_origin_blocked(self):
        """Requests from unknown origins should be blocked with 403."""
        response = self.client.get(
            '/api/v1/properties/amenities/',
            HTTP_ORIGIN='https://malicious-bot-site.com'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Access from this origin is not permitted', response.json()['errors'])

    def test_malicious_scanner_user_agent_blocked(self):
        """Automated vulnerability scanners should be blocked."""
        response = self.client.get(
            '/api/v1/properties/amenities/',
            HTTP_USER_AGENT='sqlmap/1.4.7#stable (http://sqlmap.org)'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('suspicious client signature', response.json()['errors'])

    def test_exempt_paths_pass(self):
        """Documentation and admin should be accessible."""
        response = self.client.get('/api/v1/documentation/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
