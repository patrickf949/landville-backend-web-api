"""
Threaded task backend for Django 6.0's native django.tasks framework.

Executes enqueued tasks in background worker threads so that HTTP requests
(e.g. user registration, password reset, property enquiries) never block
on I/O such as SMTP email dispatch.
"""
from concurrent.futures import ThreadPoolExecutor
import logging
import time

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
    Supports automatic retries with exponential backoff for resilient background execution.
    """

    task_class = Task

    def __init__(self, alias, params):
        super().__init__(alias, params)
        max_workers = int(self.options.get("MAX_WORKERS", 4))
        self.max_retries = int(self.options.get("MAX_RETRIES", 3))
        self.retry_backoff = float(self.options.get("RETRY_BACKOFF", 1.0))
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="django-task-worker",
        )

    def _run_in_worker(self, task_result, max_retries=None, backoff=None):
        """
        Execute the task in a worker thread with retry capability.
        Database connections are properly closed before and after each attempt
        to avoid connection leaks across worker thread lifecycles.
        """
        func = getattr(task_result.task, "func", None)
        if max_retries is None:
            max_retries = getattr(func, "max_retries", self.max_retries)
        if backoff is None:
            backoff = getattr(func, "retry_backoff", self.retry_backoff)

        attempt = 0
        while True:
            close_old_connections()
            try:
                self._execute_task(task_result)
            except Exception:
                logger.exception(
                    "Unexpected exception executing task %s on attempt %d",
                    getattr(task_result.task, "name", "unknown"),
                    attempt + 1,
                )
            finally:
                close_old_connections()

            if task_result.status == TaskResultStatus.SUCCESSFUL:
                if attempt > 0:
                    logger.info(
                        "Task %s succeeded on retry attempt %d",
                        getattr(task_result.task, "name", "unknown"),
                        attempt + 1,
                    )
                break

            attempt += 1
            if attempt > max_retries:
                logger.error(
                    "Background task %s failed after %d attempts. Errors: %s",
                    getattr(task_result.task, "name", "unknown"),
                    attempt,
                    getattr(task_result, "errors", []),
                )
                break

            delay = backoff * (2 ** (attempt - 1))
            logger.warning(
                "Background task %s failed (attempt %d/%d). Retrying in %.2fs...",
                getattr(task_result.task, "name", "unknown"),
                attempt,
                max_retries,
                delay,
            )
            if delay > 0:
                time.sleep(delay)

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
