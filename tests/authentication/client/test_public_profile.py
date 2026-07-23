"""Tests for the public profile endpoint (US-1.3)."""
from django.urls import reverse
from rest_framework import status

from authentication.models import UserProfile
from tests.authentication.client.test_base import BaseTest
from tests.factories.property_factory import PropertyFactory


class TestPublicProfile(BaseTest):
    """A user's public profile exposes their available listings only."""

    def setUp(self):
        super().setUp()
        UserProfile.objects.get_or_create(
            user=self.user, defaults={'bio': 'Trusted local landlord'})
        self.public_profile_url = reverse(
            'auth:public-profile', args=[self.user.pk])

    def test_public_profile_lists_available_listings(self):
        """An available, published listing shows up on the profile."""
        PropertyFactory.create(
            owner=self.user, is_published=True, status='AV')
        response = self.client.get(self.public_profile_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profile = response.data['data']['profile']
        self.assertEqual(profile['active_listings_count'], 1)
        self.assertEqual(len(profile['active_listings']), 1)
        self.assertEqual(profile['user']['id'], self.user.pk)

    def test_public_profile_requires_no_authentication(self):
        """The endpoint is reachable without a token."""
        response = self.client.get(self.public_profile_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_public_profile_excludes_unpublished_and_closed(self):
        """Draft, rented and sold listings are hidden from the public."""
        PropertyFactory.create(
            owner=self.user, is_published=False, status='AV')
        PropertyFactory.create(
            owner=self.user, is_published=True, status='SO')
        PropertyFactory.create(
            owner=self.user, is_published=True, status='RE')
        response = self.client.get(self.public_profile_url, format='json')
        self.assertEqual(
            response.data['data']['profile']['active_listings_count'], 0)

    def test_public_profile_missing_user_returns_404(self):
        """A non-existent user id returns 404."""
        url = reverse('auth:public-profile', args=[999999])
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
