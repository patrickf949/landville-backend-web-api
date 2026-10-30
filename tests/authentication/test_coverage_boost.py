from unittest.mock import MagicMock, patch
from django.urls import reverse
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.contrib.messages.storage.fallback import FallbackStorage
from rest_framework import status, serializers
from rest_framework.test import APITestCase, APIRequestFactory

from authentication.models import User, Client, UserProfile
from authentication.permissions import IsOwnerOrAdmin
from authentication.renderer import ClientJSONRenderer
from authentication.authorization_helper import generate_validation_url
from authentication.serializers import TwitterAuthAPISerializer, ProfileSerializer
from authentication.admin import UserCreationForm, ClientAdmin
from authentication.views import RetrieveUpdateDeleteClientView
from landville.views import error_404
import landville.asgi
from tests.factories.authentication_factory import UserFactory, ClientFactory, UserProfileFactory


class AuthCoverageBoostTests(APITestCase):

    def setUp(self):
        self.rf = APIRequestFactory()
        self.user = UserFactory.create(role='BY')
        self.admin = UserFactory.create(role='LA')
        self.client_admin = UserFactory.create(role='CA')
        self.client_company = ClientFactory.create(
            client_name='Test Realty Corp',
            email='realty@test.com',
            phone='+254 711 2233445',
            client_admin=self.client_admin,
            approval_status='pending'
        )

    def auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {user.token}')

    def test_is_owner_or_admin_permission(self):
        perm = IsOwnerOrAdmin()
        req = self.rf.get('/')

        # LA user
        req.user = self.admin
        self.assertTrue(perm.has_object_permission(req, None, self.client_company))

        # client_admin user
        req.user = self.client_admin
        self.assertTrue(perm.has_object_permission(req, None, self.client_company))

        # stranger user
        req.user = self.user
        self.assertFalse(perm.has_object_permission(req, None, self.client_company))

    def test_client_json_renderer_non_dict(self):
        renderer = ClientJSONRenderer()
        output = renderer.render("Just a text message")
        self.assertIn('"message": "Just a text message"', output)

    def test_authorization_helper_jwt_bytes(self):
        req = RequestFactory().get('/')
        with patch('jwt.encode', return_value=b'mock.jwt.token'):
            url = generate_validation_url([req, 'user@test.com'], user_id=self.user.pk)
            self.assertIn('mock.jwt.token', url)

    def test_social_auth_serializer_validation_error(self):
        serializer = TwitterAuthAPISerializer()
        mock_info = {'id_str': '12345', 'email': 'newtw@test.com', 'name': 'Twitter User'}
        with patch('authentication.socialvalidators.SocialValidation.twitter_auth_validation', return_value=mock_info):
            with patch('authentication.serializers.SocialAuthProfileUpdate.get_user_info'):
                with patch('authentication.models.User.objects.create_user', side_effect=ValidationError("DB error")):
                    with self.assertRaises(serializers.ValidationError) as cm:
                        serializer.validate({
                            'access_token': 'token123',
                            'access_token_secret': 'secret123'
                        })
                    self.assertIn('Error While creating User', str(cm.exception))

    def test_user_profile_serializer_without_next_of_kin(self):
        profile = UserProfile.objects.filter(user=self.user).first()
        if not profile:
            profile = UserProfileFactory.create(user=self.user)
        serializer = ProfileSerializer(instance=profile, data={'bio': 'New bio'}, partial=True)
        self.assertTrue(serializer.is_valid())
        updated = serializer.save()
        self.assertEqual(updated.bio, 'New bio')

    def test_user_creation_form_commit_false(self):
        form = UserCreationForm(data={
            'email': 'newformuser@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'Password@123',
            'password2': 'Password@123'
        })
        self.assertTrue(form.is_valid())
        user_uncommitted = form.save(commit=False)
        self.assertEqual(user_uncommitted.email, 'newformuser@test.com')
        self.assertIsNone(user_uncommitted.pk)

    def test_client_admin_response_post_save_change(self):
        client_admin_obj = ClientAdmin(Client, AdminSite())
        req = RequestFactory().post('/')
        # Attach messages storage
        setattr(req, 'session', 'session')
        messages_storage = FallbackStorage(req)
        setattr(req, '_messages', messages_storage)

        # 1. Approved status
        self.client_company.approval_status = 'approved'
        with patch('authentication.admin.send_email_notification.delay') as mock_email:
            with patch.object(client_admin_obj, '_response_post_save', return_value='response_ok'):
                res_app = client_admin_obj.response_post_save_change(req, self.client_company)
                mock_email.assert_called_once()
                self.assertEqual(res_app, 'response_ok')

        # 2. Rejected status
        self.client_company.approval_status = 'rejected'
        res_rej = client_admin_obj.response_post_save_change(req, self.client_company)
        self.assertEqual(res_rej.status_code, 302)
        self.assertIn('/api/v1/auth/admin/notes/', res_rej.url)

    def test_client_views_patch_and_delete(self):
        self.auth(self.client_admin)

        # 1. ClientCreateView PATCH
        patch_payload = {
            'client_name': 'Updated Realty Corp',
            'phone': '+254 711 2233445',
            'address': {'State': 'Nairobi', 'Street': 'Kenyatta Ave', 'City': 'Nairobi'}
        }
        res_patch = self.client.patch(
            reverse('authentication:client'),
            patch_payload,
            format='json'
        )
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.client_company.refresh_from_db()
        self.assertEqual(self.client_company.client_name, 'Updated Realty Corp')

        # 2. RetrieveUpdateDeleteClientView GET, PATCH, DELETE
        res_get = self.client.get(reverse('authentication:list-company', args=[self.client_company.id]))
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)

        res_patch_detail = self.client.patch(
            reverse('authentication:list-company', args=[self.client_company.id]),
            {
                'client_name': 'Updated Realty Corp',
                'phone': '+254 799 8877665',
                'address': {'State': 'Nairobi', 'Street': 'Kenyatta Ave', 'City': 'Nairobi'}
            },
            format='json'
        )
        self.assertEqual(res_patch_detail.status_code, status.HTTP_200_OK)
        self.client_company.refresh_from_db()
        self.assertEqual(self.client_company.phone, '+254 799 8877665')

        res_del_detail = self.client.delete(
            reverse('authentication:list-company', args=[self.client_company.id])
        )
        self.assertEqual(res_del_detail.status_code, status.HTTP_200_OK)

        # 3. RetrieveUpdateDeleteClientView 404
        res_404 = self.client.get(reverse('authentication:list-company', args=[999999]))
        self.assertEqual(res_404.status_code, status.HTTP_404_NOT_FOUND)

        # 4. ClientCreateView DELETE when company is gone -> 404
        res_del_empty = self.client.delete(reverse('authentication:client'))
        self.assertEqual(res_del_empty.status_code, status.HTTP_404_NOT_FOUND)

        # 5. ClientCreateView DELETE when company exists -> 200
        new_comp = ClientFactory.create(
            client_name='Another Corp',
            email='another@test.com',
            phone='+254 711 2233555',
            client_admin=self.client_admin
        )
        res_del_ok = self.client.delete(reverse('authentication:client'))
        self.assertEqual(res_del_ok.status_code, status.HTTP_200_OK)

    def test_public_profile_without_user_profile(self):
        user_no_profile = UserFactory.create()
        UserProfile.objects.filter(user=user_no_profile).delete()

        res = self.client.get(reverse('authentication:public-profile', args=[user_no_profile.id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('profile', res.data['data'])

    def test_landville_views_and_asgi(self):
        req = RequestFactory().get('/non-existent-page')
        res = error_404(req, Exception("Page not found"))
        self.assertEqual(res.status_code, 404)
        self.assertIn('documentation', res.content.decode())

        self.assertIsNotNone(landville.asgi.application)
