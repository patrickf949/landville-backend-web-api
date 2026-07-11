"""Websocket consumer tests. These use the in-memory channel layer."""
import pytest
from channels.testing import WebsocketCommunicator

from atterville.asgi import application
from chat.models import Conversation
from tests.factories.authentication_factory import UserFactory
from tests.factories.property_factory import PropertyFactory


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestChatConsumer:

    async def _connect(self, conversation, user):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/chat/{conversation.pk}/?token={user.token}')
        connected, _ = await communicator.connect()
        return communicator, connected

    async def test_participant_can_connect_and_exchange_messages(self):
        owner = UserFactory.create()
        seeker = UserFactory.create()
        listing = PropertyFactory.create(owner=owner, is_published=True)
        conversation = Conversation.objects.create(
            listing=listing, initiator=seeker)

        comm_owner, ok_owner = await self._connect(conversation, owner)
        comm_seeker, ok_seeker = await self._connect(conversation, seeker)
        assert ok_owner and ok_seeker

        await comm_seeker.send_json_to(
            {'type': 'message.send', 'body': 'Hello!'})
        event = await comm_owner.receive_json_from()
        assert event['type'] == 'message.new'
        assert event['message']['body'] == 'Hello!'

        await comm_owner.disconnect()
        await comm_seeker.disconnect()

    async def test_non_participant_is_rejected(self):
        owner = UserFactory.create()
        seeker = UserFactory.create()
        stranger = UserFactory.create()
        listing = PropertyFactory.create(owner=owner, is_published=True)
        conversation = Conversation.objects.create(
            listing=listing, initiator=seeker)

        communicator, connected = await self._connect(conversation, stranger)
        assert not connected

    async def test_anonymous_connection_is_rejected(self):
        owner = UserFactory.create()
        seeker = UserFactory.create()
        listing = PropertyFactory.create(owner=owner, is_published=True)
        conversation = Conversation.objects.create(
            listing=listing, initiator=seeker)

        communicator = WebsocketCommunicator(
            application, f'/ws/chat/{conversation.pk}/')
        connected, _ = await communicator.connect()
        assert not connected
