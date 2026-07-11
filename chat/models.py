from django.db import models

from authentication.models import User
from property.models import Property
from utils.models import BaseAbstractModel


class Conversation(BaseAbstractModel):
    """A text-only conversation between a listing owner and an
    interested user, always attached to one listing."""

    listing = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='conversations')
    initiator = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='conversations_started')
    is_blocked = models.BooleanField(default=False)
    blocked_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='conversations_blocked')
    is_reported = models.BooleanField(default=False)

    objects = models.Manager()

    class Meta:
        unique_together = ('listing', 'initiator')
        ordering = ['-updated_at']

    @property
    def owner(self):
        """The listing owner is always the other side of the thread."""
        return self.listing.owner

    def participants(self):
        return {self.initiator_id, self.listing.owner_id}

    def is_participant(self, user):
        return user.pk in self.participants()

    def __str__(self):
        return (f'Conversation about {self.listing.title} between '
                f'{self.initiator} and {self.listing.owner}')


class Message(BaseAbstractModel):
    """A single plain-text chat message."""

    MAX_LENGTH = 2000

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='messages_sent')
    body = models.TextField(max_length=MAX_LENGTH)
    read_at = models.DateTimeField(null=True, blank=True)

    objects = models.Manager()

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Message by {self.sender} in conversation {self.conversation_id}'
