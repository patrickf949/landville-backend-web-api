from unittest.mock import MagicMock, AsyncMock, patch
from django.urls import reverse
from django.test import TransactionTestCase
from rest_framework import status, serializers
from rest_framework.test import APIClient
from asgiref.sync import async_to_sync, sync_to_async

from authentication.models import BlackList, User
from chat.models import Conversation, Message
from chat.serializers import MessageSerializer
from chat.middleware import get_user, JWTAuthMiddleware
from chat.consumers import ChatConsumer
from tests.factories.authentication_factory import UserFactory
from tests.factories.property_factory import PropertyFactory


class ChatCoverageBoostTests(TransactionTestCase):

    def setUp(self):
        self.client = APIClient()
        self.owner = UserFactory.create()
        self.seeker = UserFactory.create()
        self.stranger = UserFactory.create()
        self.listing = PropertyFactory.create(owner=self.owner, is_published=True)
        self.conversation = Conversation.objects.create(
            listing=self.listing, initiator=self.seeker)

    def auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {user.token}')

    def test_chat_models_and_serializers(self):
        # Models coverage
        self.assertEqual(self.conversation.owner, self.owner)
        self.assertIn("Conversation about", str(self.conversation))

        msg = Message.objects.create(
            conversation=self.conversation,
            sender=self.seeker,
            body="Test message"
        )
        self.assertIn("Message by", str(msg))

        # Serializer max length validation
        long_body = "x" * 2001
        serializer = MessageSerializer()
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.validate_body(long_body)
        self.assertIn('cannot be longer than', str(cm.exception))

    def test_chat_views_edge_cases(self):
        # Start conversation with non-existent listing
        self.auth(self.seeker)
        res = self.client.post(reverse('chat:chat_start', args=['non-existent-slug']))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        # Message list with invalid conversation id
        res = self.client.get(reverse('chat:chat_messages', args=[999999]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        # Message post with invalid conversation id
        res = self.client.post(reverse('chat:chat_messages', args=[999999]), {'body': 'hello'})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        # Message post on blocked conversation
        self.conversation.is_blocked = True
        self.conversation.save()
        res = self.client.post(reverse('chat:chat_messages', args=[self.conversation.pk]), {'body': 'hello'})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('blocked', res.data['errors'])

        # Report conversation with invalid pk or stranger
        res = self.client.post(reverse('chat:chat_report', args=[999999]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        self.auth(self.stranger)
        res = self.client.post(reverse('chat:chat_report', args=[self.conversation.pk]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        # Block conversation with invalid pk or stranger
        res = self.client.post(reverse('chat:chat_block', args=[999999]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        res = self.client.post(reverse('chat:chat_block', args=[self.conversation.pk]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        from chat.views import MessageListCreateView
        from rest_framework.test import APIRequestFactory
        rf = APIRequestFactory()
        view = MessageListCreateView()
        view.request = rf.get('/')
        view.request.user = self.owner
        view.kwargs = {'pk': 999999}
        self.assertEqual(view.get_queryset().count(), 0)

    def test_chat_middleware(self):
        # Invalid token
        user = async_to_sync(get_user)("invalid.jwt.token")
        self.assertFalse(user.is_authenticated)

        # Inactive user
        inactive_user = UserFactory.create(is_active=False)
        user = async_to_sync(get_user)(inactive_user.token)
        self.assertFalse(user.is_authenticated)

        # Blacklisted token
        BlackList.objects.create(token=self.seeker.token)
        user = async_to_sync(get_user)(self.seeker.token)
        self.assertFalse(user.is_authenticated)

        # Valid active token
        user = async_to_sync(get_user)(self.owner.token)
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.pk, self.owner.pk)

        # Inner middleware execution without token
        inner_called = False
        async def fake_inner(scope, receive, send):
            nonlocal inner_called
            inner_called = True
            return scope
        mw = JWTAuthMiddleware(fake_inner)
        scope = {'query_string': b''}
        async_to_sync(mw)(scope, None, None)
        self.assertTrue(inner_called)
        self.assertFalse(scope['user'].is_authenticated)

    def test_chat_consumer_unit(self):
        consumer = ChatConsumer()
        consumer.scope = {
            'user': self.owner,
            'url_route': {'kwargs': {'conversation_id': self.conversation.pk}}
        }
        consumer.channel_layer = AsyncMock()
        consumer.channel_name = 'test_channel'
        consumer.close = AsyncMock()
        consumer.accept = AsyncMock()
        consumer.send_json = AsyncMock()

        async def run_consumer_tests():
            # 1. connect participant
            await consumer.connect()
            consumer.accept.assert_awaited_once()

            # 1b. connect non-existent conversation
            consumer.scope['url_route']['kwargs']['conversation_id'] = 999999
            await consumer.connect()
            consumer.close.assert_awaited_with(code=4403)
            consumer.scope['url_route']['kwargs']['conversation_id'] = self.conversation.pk

            # 2. connect non-participant
            consumer.scope['user'] = self.stranger
            await consumer.connect()
            consumer.close.assert_awaited_with(code=4403)

            # 3. connect unauthenticated
            from django.contrib.auth.models import AnonymousUser
            consumer.scope['user'] = AnonymousUser()
            await consumer.connect()
            consumer.close.assert_awaited_with(code=4401)

            # Restore owner
            consumer.scope['user'] = self.owner
            consumer.user = self.owner

            # 4. receive_json message.send valid
            await consumer.receive_json({'type': 'message.send', 'body': 'Hello WS'})
            consumer.channel_layer.group_send.assert_awaited()

            # 5. receive_json message.send invalid (empty)
            await consumer.receive_json({'type': 'message.send', 'body': '   '})
            consumer.send_json.assert_awaited_with({
                'type': 'error',
                'detail': 'Message could not be saved. Only plain, non-empty text up to 2000 characters is allowed.'
            })

            # 6. receive_json message.read
            await consumer.receive_json({'type': 'message.read'})

            # 6b. receive_json unknown event
            await consumer.receive_json({'type': 'unknown.event'})

            # 7. receive_json message.send when blocked
            self.conversation.is_blocked = True
            await sync_to_async(self.conversation.save)()
            await consumer.receive_json({'type': 'message.send', 'body': 'Blocked message'})
            consumer.send_json.assert_awaited_with({
                'type': 'error',
                'detail': 'This conversation has been blocked.'
            })

            # 8. broadcast handlers
            await consumer.message_new({'message': {'body': 'new'}})
            consumer.send_json.assert_awaited_with({'type': 'message.new', 'message': {'body': 'new'}})

            await consumer.message_read({'reader_id': 123})
            consumer.send_json.assert_awaited_with({'type': 'message.read', 'reader_id': 123})

            # 9. disconnect
            await consumer.disconnect(1000)
            consumer.channel_layer.group_discard.assert_awaited()

        async_to_sync(run_consumer_tests)()
