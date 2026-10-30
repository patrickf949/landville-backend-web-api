"""Background task handlers for Landville."""
import functools

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.tasks import task as django_task
from django.template.loader import render_to_string


class TaskCallable:
    """
    Callable wrapper around a Django 6.0 Task object.
    Provides:
    - Direct invocation via `send_email_notification(...)`
    - Background enqueue via `send_email_notification.delay(...)`
    - Standard attribute mutability so `@patch('utils.tasks.send_email_notification.delay')`
      works without issue in unit tests.
    - Exposes retry metadata (max_retries, retry_backoff).
    """

    def __init__(self, task_instance, max_retries=3, retry_backoff=1.0):
        self._task = task_instance
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        functools.update_wrapper(self, task_instance.func)
        try:
            task_instance.func.max_retries = max_retries
            task_instance.func.retry_backoff = retry_backoff
        except (AttributeError, TypeError):
            pass

    def __call__(self, *args, **kwargs):
        return self._task.call(*args, **kwargs)

    def delay(self, *args, **kwargs):
        return self._task.enqueue(*args, **kwargs)

    def enqueue(self, *args, **kwargs):
        return self._task.enqueue(*args, **kwargs)


def task(fn=None, *, max_retries=3, retry_backoff=1.0, **task_kwargs):
    """Task decorator wrapping Django 6.0's task in a TaskCallable with retry support."""
    def decorator(func):
        django_task_obj = django_task(func, **task_kwargs)
        return TaskCallable(
            django_task_obj,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
        )

    if fn is not None:
        return decorator(fn)
    return decorator


@task(max_retries=3, retry_backoff=1.0)
def send_email_notification(body):
    """
    Handles sending of notifications to the user via email in a background worker thread.
    Arguments:
        body: {
            subject: "",
            recipient: ["test1@t.c","test2@t.c"], # an array or emails
            text_body: "", # Sample text email template
            html_body: "", # Sample html email template
            context: {} # A dict to be used as the template's context for
                          rendering.
        }
    :param body:
    :return: Null
    """
    text_body = render_to_string(body['text_body'], body['context'])
    html_body = render_to_string(body['html_body'], body['context'])

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or "noreply@landville.com"
    if '<' not in from_email:
        from_email = f"Landville <{from_email}>"

    msg = EmailMultiAlternatives(
        subject=body['subject'],
        from_email=from_email,
        to=body['recipient'],
        body=text_body
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
