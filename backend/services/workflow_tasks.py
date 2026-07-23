from __future__ import annotations

from core.database import SessionLocal
from workflows import WorkflowOrchestrator


def execute_workflow_run(run_id: str) -> None:
    with SessionLocal() as db:
        WorkflowOrchestrator(db).execute(run_id)

