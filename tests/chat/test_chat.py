"""Tests for the text-only chat between listing owners and seekers."""
import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chat.models import Conversation, Message
from tests.factories.authentication_factory import UserFactory
from tests.factories.property_factory import PropertyFactory


class ChatBaseTest(APITestCase):

    def setUp(self):
        self.owner = UserFactory.create()
        self.seeker = UserFactory.create()
        self.stranger = UserFactory.create()
        self.listing = PropertyFactory.create(
            owner=self.owner, is_published=True)
        self.conversation = Conversation.objects.create(
            listing=self.listing, initiator=self.seeker)
        self.inbox_url = reverse('chat:chat_inbox')
        self.messages_url = reverse(
            'chat:chat_messages', args=[self.conversation.pk])

    def auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {user.token}')


class ConversationTest(ChatBaseTest):

    def test_seeker_can_start_conversation(self):
        self.auth(self.stranger)
        url = reverse('chat:chat_start', args=[self.listing.slug])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_starting_twice_reuses_the_same_conversation(self):
        self.auth(self.seeker)
        url = reverse('chat:chat_start', args=[self.listing.slug])
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(Conversation.objects.filter(
            listing=self.listing, initiator=self.seeker).count(), 1)

    def test_owner_cannot_chat_about_own_listing(self):
        self.auth(self.owner)
        url = reverse('chat:chat_start', args=[self.listing.slug])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inbox_lists_conversations_for_both_parties(self):
        for user in (self.owner, self.seeker):
            self.auth(user)
            response = self.client.get(self.inbox_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stranger_has_empty_inbox(self):
        self.auth(self.stranger)
        response = self.client.get(self.inbox_url)
        body = json.loads(response.content)
        results = body.get('results', body)
        self.assertEqual(len(results), 0)


class MessageTest(ChatBaseTest):

    def test_participant_can_send_and_read_messages(self):
        self.auth(self.seeker)
        response = self.client.post(
            self.messages_url, {'body': 'Hello, is this still available?'},
            format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.auth(self.owner)
        response = self.client.get(self.messages_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_participant_cannot_access_messages(self):
        self.auth(self.stranger)
        response = self.client.get(self.messages_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_markup_is_stripped_from_messages(self):
        self.auth(self.seeker)
        self.client.post(
            self.messages_url,
            {'body': '<script>alert(1)</script>Hi there'}, format='json')
        message = Message.objects.last()
        self.assertNotIn('<script>', message.body)

    def test_empty_messages_are_rejected(self):
        self.auth(self.seeker)
        response = self.client.post(
            self.messages_url, {'body': '<b></b>  '}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reading_thread_marks_messages_read(self):
        Message.objects.create(
            conversation=self.conversation, sender=self.seeker, body='hi')
        self.auth(self.owner)
        self.client.get(self.messages_url)
        self.assertIsNotNone(Message.objects.last().read_at)

    def test_blocked_conversation_rejects_messages(self):
        self.auth(self.owner)
        block_url = reverse('chat:chat_block', args=[self.conversation.pk])
        self.client.post(block_url)
        self.auth(self.seeker)
        response = self.client.post(
            self.messages_url, {'body': 'hello?'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_participant_can_report_conversation(self):
        self.auth(self.owner)
        url = reverse('chat:chat_report', args=[self.conversation.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.conversation.refresh_from_db()
        self.assertTrue(self.conversation.is_reported)
