from celery import shared_task

from .availability import release_expired_holds as _release
from .retention import purge_expired_documents as _purge


@shared_task
def release_expired_holds() -> int:
    return _release()


@shared_task
def purge_expired_documents() -> int:
    return _purge()
