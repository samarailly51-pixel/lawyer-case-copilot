from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from core.database import SessionLocal, init_db
from evaluation.labeled import evaluate_annotation


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate authorized, de-identified, dual-reviewed case annotations locally.")
    parser.add_argument("annotation_file", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source_bytes = args.annotation_file.read_bytes()
    records = [json.loads(line) for line in source_bytes.decode("utf-8").splitlines() if line.strip()]
    init_db()
    with SessionLocal() as db:
        results = [evaluate_annotation(db, record) for record in records]
    eligible = [item for item in results if item.get("eligible")]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_label": "经授权、已脱敏、双人复核真实案例集",
        "annotation_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "record_count": len(records),
        "eligible_count": len(eligible),
        "rejected_count": len(records) - len(eligible),
        "macro_f1": round(sum(item["macro_f1"] for item in eligible) / len(eligible), 4) if eligible else None,
        "results": results,
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(content + "\n", encoding="utf-8")
    else:
        print(content)


if __name__ == "__main__":
    main()
