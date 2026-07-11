"""Websocket consumer for text-only property chats."""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils.timezone import now

from chat.models import Conversation, Message
from chat.serializers import MessageSerializer


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """One websocket connection per open conversation."""

    async def connect(self):
        self.user = self.scope.get('user')
        self.conversation_id = int(
            self.scope['url_route']['kwargs']['conversation_id'])
        self.group_name = f'chat_{self.conversation_id}'

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4401)
            return

        allowed = await self._is_participant()
        if not allowed:
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        """Handle events from the client.
        {type: 'message.send', body: '...'} -> broadcast 'message.new'
        {type: 'message.read'}              -> broadcast 'message.read'
        """
        event_type = content.get('type')
        if event_type == 'message.send':
            blocked = await self._is_blocked()
            if blocked:
                await self.send_json({
                    'type': 'error',
                    'detail': 'This conversation has been blocked.'})
                return
            message = await self._save_message(content.get('body', ''))
            if message is None:
                await self.send_json({
                    'type': 'error',
                    'detail': 'Message could not be saved. Only plain, '
                              'non-empty text up to 2000 characters '
                              'is allowed.'})
                return
            await self.channel_layer.group_send(self.group_name, {
                'type': 'message.new',
                'message': message,
            })
        elif event_type == 'message.read':
            await self._mark_read()
            await self.channel_layer.group_send(self.group_name, {
                'type': 'message.read',
                'reader_id': self.user.pk,
            })

    async def message_new(self, event):
        await self.send_json({
            'type': 'message.new', 'message': event['message']})

    async def message_read(self, event):
        await self.send_json({
            'type': 'message.read', 'reader_id': event['reader_id']})

    # ------------------------------------------------------------------
    @database_sync_to_async
    def _is_participant(self):
        try:
            conversation = Conversation.objects.select_related(
                'listing').get(pk=self.conversation_id, is_deleted=False)
        except Conversation.DoesNotExist:
            return False
        self._conversation_pk = conversation.pk
        return conversation.is_participant(self.user)

    @database_sync_to_async
    def _is_blocked(self):
        return Conversation.objects.filter(
            pk=self.conversation_id, is_blocked=True).exists()

    @database_sync_to_async
    def _save_message(self, body):
        conversation = Conversation.objects.get(pk=self.conversation_id)
        serializer = MessageSerializer(data={'body': body})
        if not serializer.is_valid():
            return None
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            body=serializer.validated_data['body'])
        # touch the conversation so inbox ordering is correct
        conversation.save(update_fields=['updated_at'])
        return MessageSerializer(message).data

    @database_sync_to_async
    def _mark_read(self):
        Message.objects.filter(
            conversation_id=self.conversation_id,
            read_at__isnull=True).exclude(sender=self.user).update(
            read_at=now())
