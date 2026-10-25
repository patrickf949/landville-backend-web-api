"""
Threaded task backend for Django 6.0's native django.tasks framework.

Executes enqueued tasks in background worker threads so that HTTP requests
(e.g. user registration, password reset, property enquiries) never block
on I/O such as SMTP email dispatch.
"""
from concurrent.futures import ThreadPoolExecutor
import logging

from django.db import close_old_connections
from django.tasks.backends.immediate import ImmediateBackend
from django.tasks.base import Task, TaskResult, TaskResultStatus
from django.utils.crypto import get_random_string

logger = logging.getLogger(__name__)


class ThreadedTaskBackend(ImmediateBackend):
    """
    A Django 6.0 task backend that offloads task execution to a managed
    ThreadPoolExecutor while maintaining full Django task lifecycle events,
    TaskResult status transitions, exception captures, and task signals.
    """

    task_class = Task

    def __init__(self, alias, params):
        super().__init__(alias, params)
        max_workers = int(self.options.get("MAX_WORKERS", 4))
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="django-task-worker",
        )

    def _run_in_worker(self, task_result):
        """
        Execute the task in a worker thread, ensuring database connections
        are properly closed before and after execution to avoid connection leaks.
        """
        close_old_connections()
        try:
            self._execute_task(task_result)
        except Exception:
            logger.exception("Error executing background task %s", task_result.task.name)
        finally:
            close_old_connections()

    def enqueue(self, task, args, kwargs):
        self.validate_task(task)

        task_result = TaskResult(
            task=task,
            id=get_random_string(32),
            status=TaskResultStatus.READY,
            enqueued_at=None,
            started_at=None,
            last_attempted_at=None,
            finished_at=None,
            args=args,
            kwargs=kwargs,
            backend=self.alias,
            errors=[],
            worker_ids=[],
        )

        # Offload to worker thread pool
        self._executor.submit(self._run_in_worker, task_result)
        return task_result
