from __future__ import annotations

import argparse
import json

from core.database import SessionLocal, init_db
from evaluation.metrics import evaluate_case


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate traceability and review quality for one case.")
    parser.add_argument("case_id")
    args = parser.parse_args()
    init_db()
    with SessionLocal() as db:
        print(json.dumps(evaluate_case(db, args.case_id).to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

