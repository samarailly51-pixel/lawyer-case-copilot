from __future__ import annotations

import logging
import signal
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from core.database import SessionLocal, init_db
from models.entities import AgentRun
from workflows import WorkflowOrchestrator


logger = logging.getLogger("lawyer_case_copilot.worker")
logging.basicConfig(level=logging.INFO, format="%(message)s")
running = True


def _stop(*_args) -> None:
    global running
    running = False


def claim_next_run() -> str | None:
    stale_before = datetime.now(timezone.utc) - timedelta(minutes=10)
    with SessionLocal() as db:
        statement = select(AgentRun).where(or_(
            AgentRun.status == "pending",
            (AgentRun.status == "claimed") & (AgentRun.started_at < stale_before),
        )).order_by(AgentRun.created_at).limit(1)
        if db.bind and db.bind.dialect.name == "postgresql":
            statement = statement.with_for_update(skip_locked=True)
        run = db.scalar(statement)
        if not run:
            return None
        run.status = "claimed"
        run.started_at = datetime.now(timezone.utc)
        db.commit()
        return run.id


def main() -> None:
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    init_db()
    logger.info('{"event":"worker_started"}')
    while running:
        run_id = claim_next_run()
        if not run_id:
            time.sleep(2)
            continue
        logger.info('{"event":"workflow_claimed","run_id":"%s"}', run_id)
        try:
            with SessionLocal() as db:
                WorkflowOrchestrator(db).execute(run_id)
        except Exception:
            logger.exception('{"event":"workflow_worker_error","run_id":"%s"}', run_id)
    logger.info('{"event":"worker_stopped"}')


if __name__ == "__main__":
    main()

