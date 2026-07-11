from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


class Term(models.Model):
    """Define behaviour and Properties of a Terms and Conditions Instance."""

    details = CKEditor5Field(blank=True, null=True)
    last_updated_at = models.DateField(auto_now=True)

    class Meta:
        verbose_name = 'Terms and Conditions'
        verbose_name_plural = 'Terms and Conditions'

    def __str__(self):
        return 'Terms and Conditions'
