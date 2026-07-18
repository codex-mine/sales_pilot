"""
Celery tasks for the Email Sending module (the `sending` queue).

Two tasks:
- `dispatch_due_scheduled_emails` — a periodic (Celery beat) task that finds
  SCHEDULED emails whose `scheduled_at` has passed (`FOR UPDATE SKIP LOCKED`,
  see `models/ARCHITECTURE.md` §3) and fans a per-row send task out for each.
  The per-row dispatches are enqueued *before* this transaction commits, so
  the row locks are still held while dispatching — a concurrent overlapping
  beat tick's own SKIP LOCKED select naturally skips these same rows instead
  of double-dispatching them.
- `send_scheduled_email_task` — processes exactly one row via
  `EmailSendingService.process_scheduled`, which re-locks and re-checks
  status itself, so redelivery/duplicate dispatch is a safe no-op.

Neither task calls a sender-provider SDK directly — both go through
`EmailSendingService`, which is the only caller of
`app.services.email.sender_client`.
"""

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.email_repository import EmailRepository
from app.repositories.user_repository import UserRepository
from app.workers.celery_app import celery_app
from app.workers.session_utils import run_with_fresh_session


@celery_app.task(name="sending.send_scheduled_email", acks_late=True)
def send_scheduled_email_task(email_id: str, organization_id: str) -> None:
    from app.services.email.email_sending_service import EmailSendingService

    async def _run(session: AsyncSession) -> None:
        org_uuid = uuid.UUID(organization_id)
        service = EmailSendingService(session)
        email = await service.emails.get_by_id(uuid.UUID(email_id), org_uuid)
        if email is None or email.sent_by is None:
            return
        actor = await UserRepository(session).get_by_id(email.sent_by)
        if actor is None:
            return
        await service.process_scheduled(uuid.UUID(email_id), org_uuid, actor)

    asyncio.run(run_with_fresh_session(_run))


@celery_app.task(name="sending.dispatch_due_scheduled_emails", acks_late=True)
def dispatch_due_scheduled_emails() -> None:
    async def _run(session: AsyncSession) -> None:
        due = await EmailRepository(session).list_due_scheduled(limit=200)
        for email in due:
            send_scheduled_email_task.apply_async(
                args=[str(email.id), str(email.organization_id)], queue="sending"
            )
        # Commit (releasing the FOR UPDATE SKIP LOCKED locks) only after every
        # row in this batch has already been enqueued — see module docstring.
        await session.commit()

    asyncio.run(run_with_fresh_session(_run))
