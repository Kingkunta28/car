from celery import shared_task

from . import services


@shared_task(acks_late=True)
def send_notification(log_id: str) -> bool:
    return services.deliver(log_id)


@shared_task
def process_notification_queue() -> int:
    """Retry failed emails whose backoff has elapsed, and any stuck in the queue."""
    count = 0
    for log_id in services.due_for_retry().values_list("pk", flat=True)[:200]:
        services.deliver(log_id)
        count += 1
    return count
