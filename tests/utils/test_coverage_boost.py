from unittest.mock import MagicMock, patch
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from rest_framework.exceptions import ValidationError

from authentication.models import User, Client
from property.models import Property
from tests.factories.authentication_factory import UserFactory
from tests.factories.property_factory import PropertyFactory
from utils import BaseUtils
from utils.client_permissions import IsownerOrReadOnly, IsClient
from utils.permissions import (
    ReadOnly, CanEditProperty, IsOwnerOrReadOnly as GenIsOwnerOrReadOnly,
    IsClientAdmin, IsBuyer, IsOwner, IsReviewer, IsBuyerOrReadOnly, IsAdmin
)
from utils.managers import ClientAccountQuery, TransactionQuery
from utils.task_backend import ThreadedTaskBackend
from utils.throttling import (
    BurstAnonRateThrottle, BurstUserRateThrottle, PostRequestRateThrottle,
    SensitiveActionRateThrottle
)
from utils.security_middleware import SecurityAndOriginProtectionMiddleware
from utils.media_handlers import CloudinaryResourceHandler
from utils.tasks import task


@task(max_retries=5, retry_backoff=0.5)
def sample_custom_task():
    return "done"


@task
def sample_default_task():
    return "done"


class UtilsCoverageBoostTests(TestCase):
    """Targeted tests to bring utils module to 100% test coverage."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = UserFactory.create()
        self.admin_user = UserFactory.create(role='LA')
        self.client_user = UserFactory.create(role='CA')
        self.buyer_user = UserFactory.create(role='BY')

    def test_client_permissions_is_owner_or_read_only(self):
        perm = IsownerOrReadOnly()
        req_get = self.factory.get('/')
        req_get.user = self.user
        req_post = self.factory.post('/')
        mock_user = MagicMock()
        req_post.user = mock_user

        obj = MagicMock()
        obj.owner = None

        self.assertTrue(perm.has_object_permission(req_get, None, obj))

        employer = MagicMock()
        mock_user.employer.first.return_value = employer
        obj.owner = employer
        self.assertTrue(perm.has_object_permission(req_post, None, obj))

        obj.owner = MagicMock()
        self.assertFalse(perm.has_object_permission(req_post, None, obj))

    def test_client_permissions_is_client(self):
        perm = IsClient()
        req_get = self.factory.get('/')
        req_post = self.factory.post('/')

        # Unauthenticated
        req_get.user = AnonymousUser()
        req_post.user = AnonymousUser()
        self.assertFalse(perm.has_permission(req_get, None))
        self.assertFalse(perm.has_permission(req_post, None))

        # Authenticated as CA
        req_get.user = self.client_user
        req_post.user = self.client_user
        self.assertTrue(perm.has_permission(req_get, None))
        self.assertTrue(perm.has_permission(req_post, None))

        # Authenticated as LA
        req_get.user = self.admin_user
        req_post.user = self.admin_user
        self.assertTrue(perm.has_permission(req_get, None))
        self.assertFalse(perm.has_permission(req_post, None))

    def test_general_permissions(self):
        # ReadOnly
        ro = ReadOnly()
        self.assertTrue(ro.has_permission(self.factory.get('/'), None))
        self.assertFalse(ro.has_permission(self.factory.post('/'), None))

        # CanEditProperty
        cep = CanEditProperty()
        listing = PropertyFactory.create(owner=self.user)
        req_get = self.factory.get('/')
        req_get.user = self.user
        self.assertTrue(cep.has_object_permission(req_get, None, listing))

        req_post = self.factory.post('/')
        req_post.user = self.user
        self.assertTrue(cep.has_object_permission(req_post, None, listing))

        req_post.user = self.admin_user
        self.assertTrue(cep.has_object_permission(req_post, None, listing))

        req_post.user = self.buyer_user
        self.assertFalse(cep.has_object_permission(req_post, None, listing))

        # GenIsOwnerOrReadOnly
        iow = GenIsOwnerOrReadOnly()
        self.assertTrue(iow.has_object_permission(req_get, None, listing))
        req_post.user = self.user
        self.assertTrue(iow.has_object_permission(req_post, None, listing))
        req_post.user = self.buyer_user
        self.assertFalse(iow.has_object_permission(req_post, None, listing))

        # IsClientAdmin
        ica = IsClientAdmin()
        req_mock = self.factory.post('/')
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = 'CA'
        client_mock = MagicMock()
        client_mock.approval_status = 'approved'
        mock_user.employer.first.return_value = client_mock
        req_mock.user = mock_user
        self.assertTrue(ica.has_permission(req_mock, None))

        client_mock.approval_status = 'pending'
        self.assertFalse(ica.has_permission(req_mock, None))

        req_anon = self.factory.post('/')
        req_anon.user = AnonymousUser()
        self.assertFalse(ica.has_permission(req_anon, None))

        # IsBuyer
        ib = IsBuyer()
        req_get.user = self.admin_user
        self.assertTrue(ib.has_permission(req_get, None))
        req_get.user = self.client_user
        self.assertTrue(ib.has_permission(req_get, None))
        req_get.user = self.buyer_user
        self.assertTrue(ib.has_permission(req_get, None))
        req_post.user = self.buyer_user
        self.assertTrue(ib.has_permission(req_post, None))
        req_post.user = self.user
        self.assertFalse(ib.has_permission(req_post, None))

        # IsOwner
        io = IsOwner()
        enq = MagicMock()
        enq.requester = self.user
        self.assertTrue(io.has_object_permission(req_get, None, enq))
        req_post.user = self.user
        self.assertTrue(io.has_object_permission(req_post, None, enq))
        req_post.user = self.buyer_user
        self.assertFalse(io.has_object_permission(req_post, None, enq))

        # IsReviewer
        ir = IsReviewer()
        rev = MagicMock()
        rev.reviewer = self.user
        self.assertTrue(ir.has_object_permission(req_get, None, rev))
        req_post.user = self.user
        self.assertTrue(ir.has_object_permission(req_post, None, rev))
        req_post.user = self.buyer_user
        self.assertFalse(ir.has_object_permission(req_post, None, rev))

        # IsBuyerOrReadOnly
        ibro = IsBuyerOrReadOnly()
        self.assertTrue(ibro.has_permission(req_get, None))
        req_post.user = self.buyer_user
        self.assertTrue(ibro.has_permission(req_post, None))
        req_post.user = self.user
        self.assertFalse(ibro.has_permission(req_post, None))

        # IsAdmin
        ia = IsAdmin()
        req_del = self.factory.delete('/')
        req_del.user = self.admin_user
        self.assertTrue(ia.has_object_permission(req_del, None, listing))
        req_del.user = self.user
        self.assertFalse(ia.has_object_permission(req_del, None, listing))
        self.assertFalse(ia.has_object_permission(req_get, None, listing))

    def test_base_utils(self):
        bu = BaseUtils()
        self.assertEqual(bu.remove_redundant_spaces("  hello   world  "), "hello world")

        # validate_dependent_fields second branch
        with self.assertRaises(ValidationError):
            bu.validate_dependent_fields({'field_b': 2}, 'field_a', 'field_b', 'err1', 'err2')

    def test_custom_managers_extra(self):
        ca_query = ClientAccountQuery(model=Client)
        with patch.object(ca_query, '_active') as mock_active:
            mock_active.return_value.filter.return_value = []
            ca_query.not_deleted('test_owner')
            mock_active.return_value.filter.assert_called_with(owner='test_owner')

            ca_query.client_admin_has_client(123)
            mock_active.return_value.filter.assert_called_with(owner_id=123)

        tx_query = TransactionQuery(model=Property)
        with patch.object(tx_query, '_active') as mock_active:
            mock_active.return_value.filter.return_value.aggregate.return_value = {'amount_paid__sum': 500}
            prop = PropertyFactory.create(owner=self.user)
            res1 = tx_query.total_amount(self.user, prop)
            self.assertEqual(res1, 500)
            res2 = tx_query.client_total_amount(prop)
            self.assertEqual(res2, 500)

    def test_task_backend_exception_handling(self):
        from django.tasks.base import TaskResultStatus
        from utils.tasks import task

        backend = ThreadedTaskBackend('test_alias', {'OPTIONS': {'MAX_WORKERS': 1, 'MAX_RETRIES': 1, 'RETRY_BACKOFF': 0}})
        mock_result = MagicMock()
        mock_result.task.name = 'broken_task'
        mock_result.status = TaskResultStatus.FAILED

        # 1. Exception during _execute_task (retries exhausted)
        with patch.object(backend, '_execute_task', side_effect=RuntimeError("Worker error")):
            with patch('utils.task_backend.close_old_connections'):
                backend._run_in_worker(mock_result, max_retries=1, backoff=0)

        # 2. Success on retry
        attempts = 0
        def fake_execute(res):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                res.status = TaskResultStatus.FAILED
            else:
                res.status = TaskResultStatus.SUCCESSFUL

        mock_success = MagicMock()
        mock_success.task.name = 'retry_task'
        mock_success.status = TaskResultStatus.FAILED
        with patch.object(backend, '_execute_task', side_effect=fake_execute):
            with patch('utils.task_backend.close_old_connections'):
                with patch('utils.task_backend.time.sleep') as mock_sleep:
                    backend._run_in_worker(mock_success, max_retries=2, backoff=0.01)
                    self.assertEqual(mock_success.status, TaskResultStatus.SUCCESSFUL)
                    self.assertEqual(attempts, 2)
                    mock_sleep.assert_called_once()

        # 3. Task decorator with custom parameters and default parameters
        self.assertEqual(sample_custom_task.max_retries, 5)
        self.assertEqual(sample_custom_task.retry_backoff, 0.5)
        self.assertEqual(sample_default_task.max_retries, 3)
        self.assertEqual(sample_default_task.retry_backoff, 1.0)

        # 4. TaskCallable exception when func attributes cannot be set
        from utils.tasks import TaskCallable
        mock_immutable_task = MagicMock()
        mock_immutable_task.func = 123  # ints don't allow setattr
        callable_obj = TaskCallable(mock_immutable_task)
        self.assertEqual(callable_obj.max_retries, 3)

    def test_throttling_classes_directly(self):
        req_get = self.factory.get('/')
        req_post = self.factory.post('/')
        req_get.user = AnonymousUser()
        req_post.user = AnonymousUser()

        # In test mode
        sens_default = SensitiveActionRateThrottle()
        self.assertTrue(sens_default.allow_request(req_post, None))

        with patch('utils.throttling.is_test_mode', return_value=False):
            anon_throttle = BurstAnonRateThrottle()
            self.assertTrue(anon_throttle.allow_request(req_get, None))

            user_throttle = BurstUserRateThrottle()
            req_user = self.factory.get('/')
            req_user.user = self.user
            self.assertTrue(user_throttle.allow_request(req_user, None))

            post_throttle = PostRequestRateThrottle()
            self.assertTrue(post_throttle.allow_request(req_get, None))

            key_anon = post_throttle.get_cache_key(req_post, None)
            self.assertIn('anon_', key_anon)

            req_post.user = self.user
            key_user = post_throttle.get_cache_key(req_post, None)
            self.assertIn('user_', key_user)

            sens_throttle = SensitiveActionRateThrottle()
            key_sens = sens_throttle.get_cache_key(req_post, None)
            self.assertIn('sensitive_action', key_sens)

            # Test actual super().allow_request execution on non-test mode
            self.assertTrue(post_throttle.allow_request(req_post, None))
            self.assertTrue(sens_throttle.allow_request(req_post, None))

    def test_security_middleware_edge_cases(self):
        mw = SecurityAndOriginProtectionMiddleware(lambda req: HttpResponse("OK"))

        # Referer fallback with allowed origin
        req = self.factory.get('/api/v1/properties/', HTTP_REFERER='https://landville.vercel.app/home')
        res = mw(req)
        self.assertEqual(res.status_code, 200)

        # Referer without netloc
        req_bad_ref = self.factory.get('/api/v1/properties/', HTTP_REFERER='about:blank')
        res_bad_ref = mw(req_bad_ref)
        self.assertEqual(res_bad_ref.status_code, 200)

        # Regex origin allowed (e.g. preview deployment)
        req_preview = self.factory.get('/api/v1/properties/', HTTP_ORIGIN='https://landville-git-feat.vercel.app')
        res_preview = mw(req_preview)
        self.assertEqual(res_preview.status_code, 200)

        # Disallowed origin
        req_evil = self.factory.get('/api/v1/properties/', HTTP_ORIGIN='https://evil-hacker.com')
        res_evil = mw(req_evil)
        self.assertEqual(res_evil.status_code, 403)

        # Localhost allowed in debug mode (custom port not in CORS_ALLOWED_ORIGINS)
        with override_settings(DEBUG=True):
            req_local = self.factory.get('/api/v1/properties/', HTTP_ORIGIN='http://localhost:9999')
            res_local = mw(req_local)
            self.assertEqual(res_local.status_code, 200)

            # Non-localhost rejected even in debug mode
            req_debug_evil = self.factory.get('/api/v1/properties/', HTTP_ORIGIN='https://evil-hacker.com')
            res_debug_evil = mw(req_debug_evil)
            self.assertEqual(res_debug_evil.status_code, 403)

    def test_media_handler_cloudinary_exceptions(self):
        uploader = CloudinaryResourceHandler()
        instance = PropertyFactory.create(owner=self.user, image_others=['http://other.com/pic1.jpg'], video='http://youtube.com/v1')

        # upload_image_from_request with empty image_main
        req = self.factory.post('/')
        req.FILES['image_main'] = None
        self.assertIsNone(uploader.upload_image_from_request(req))

        with patch.object(uploader, 'get_cloudinary_public_id', side_effect=ValidationError("Not cloudinary")):
            payload = {'image_others': ['http://other.com/pic1.jpg', 'http://not-in-db.com/pic2.jpg'], 'video': 'http://youtube.com/v1'}
            updated = uploader.delete_cloudinary_resource(instance, payload)
            self.assertEqual(instance.image_others, [])
            self.assertIsNone(instance.video)

        # delete_cloudinary_resource with no image_others, mismatched video, and valid cloudinary video
        instance2 = PropertyFactory.create(owner=self.user, image_others=[], video='http://res.cloudinary.com/demo/video/upload/sample.mp4')
        with patch.object(uploader, 'get_cloudinary_public_id', return_value='sample'):
            with patch('utils.media_handlers.delete_resources') as mock_del_res:
                uploader.delete_cloudinary_resource(instance2, {'image_others': [], 'video': 'http://res.cloudinary.com/demo/video/upload/sample.mp4'})
                mock_del_res.assert_called_once()

        # mismatched video branch
        uploader.delete_cloudinary_resource(instance2, {'image_others': None, 'video': 'http://mismatched.com/vid'})

    def test_tasks_enqueue_and_from_email(self):
        from utils.tasks import send_email_notification
        with patch('utils.task_backend.ThreadedTaskBackend.enqueue') as mock_enq:
            send_email_notification.enqueue({'test': 1})
            mock_enq.assert_called_once()

        # send_email_notification with < already in from_email
        with override_settings(DEFAULT_FROM_EMAIL="Custom Name <custom@landville.com>"):
            with patch('utils.tasks.render_to_string', return_value="hello"):
                with patch('utils.tasks.EmailMultiAlternatives') as mock_email:
                    mock_msg = MagicMock()
                    mock_email.return_value = mock_msg
                    body = {
                        'subject': 'Test',
                        'recipient': ['test@test.com'],
                        'text_body': 'template.txt',
                        'html_body': 'template.html',
                        'context': {}
                    }
                    send_email_notification(body)
                    mock_email.assert_called_once_with(
                        subject='Test',
                        from_email='Custom Name <custom@landville.com>',
                        to=['test@test.com'],
                        body='hello'
                    )
