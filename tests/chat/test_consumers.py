"""Websocket consumer tests. These use the in-memory channel layer."""
from django.test import TransactionTestCase
from channels.testing import WebsocketCommunicator
from asgiref.sync import async_to_sync

from landville.asgi import application
from chat.models import Conversation
from tests.factories.authentication_factory import UserFactory
from tests.factories.property_factory import PropertyFactory


class TestChatConsumer(TransactionTestCase):

    def test_participant_can_connect_and_exchange_messages(self):
        owner = UserFactory.create()
        seeker = UserFactory.create()
        listing = PropertyFactory.create(owner=owner, is_published=True)
        conversation = Conversation.objects.create(
            listing=listing, initiator=seeker)

        conv_pk = conversation.pk
        owner_token = owner.token
        seeker_token = seeker.token

        async def run_test():
            comm_owner = WebsocketCommunicator(
                application,
                f'/ws/chat/{conv_pk}/?token={owner_token}')
            connected_owner, _ = await comm_owner.connect()

            comm_seeker = WebsocketCommunicator(
                application,
                f'/ws/chat/{conv_pk}/?token={seeker_token}')
            connected_seeker, _ = await comm_seeker.connect()

            self.assertTrue(connected_owner)
            self.assertTrue(connected_seeker)

            await comm_seeker.send_json_to(
                {'type': 'message.send', 'body': 'Hello!'})
            event = await comm_owner.receive_json_from()
            self.assertEqual(event['type'], 'message.new')
            self.assertEqual(event['message']['body'], 'Hello!')

            await comm_owner.disconnect()
            await comm_seeker.disconnect()

        async_to_sync(run_test)()

    def test_non_participant_is_rejected(self):
        owner = UserFactory.create()
        seeker = UserFactory.create()
        stranger = UserFactory.create()
        listing = PropertyFactory.create(owner=owner, is_published=True)
        conversation = Conversation.objects.create(
            listing=listing, initiator=seeker)

        conv_pk = conversation.pk
        stranger_token = stranger.token

        async def run_test():
            comm_stranger = WebsocketCommunicator(
                application,
                f'/ws/chat/{conv_pk}/?token={stranger_token}')
            connected_stranger, _ = await comm_stranger.connect()
            self.assertFalse(connected_stranger)
            await comm_stranger.disconnect()

        async_to_sync(run_test)()

    def test_anonymous_connection_is_rejected(self):
        owner = UserFactory.create()
        seeker = UserFactory.create()
        listing = PropertyFactory.create(owner=owner, is_published=True)
        conversation = Conversation.objects.create(
            listing=listing, initiator=seeker)

        conv_pk = conversation.pk

        async def run_test():
            communicator = WebsocketCommunicator(
                application, f'/ws/chat/{conv_pk}/')
            connected, _ = await communicator.connect()
            self.assertFalse(connected)
            await communicator.disconnect()

        async_to_sync(run_test)()
