"""Run the deterministic Personal relevance benchmark without touching a DB."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app  # noqa: E402


def run() -> dict[str, object]:
    path = ROOT / "benchmarks" / "memory_relevance_cases.json"
    benchmark = json.loads(path.read_text(encoding="utf-8"))
    failures = []
    for case in benchmark["cases"]:
        fact = case["fact"]
        source_text = case["source_text"]
        entity_type = app.classify_entity_type(fact, source_text)
        relevance = app.classify_personal_relevance(fact, source_text, entity_type)
        if entity_type != case["expected_entity_type"] or relevance != case["expected_relevance"]:
            failures.append({
                "id": case["id"],
                "expected_entity_type": case["expected_entity_type"],
                "actual_entity_type": entity_type,
                "expected_relevance": case["expected_relevance"],
                "actual_relevance": relevance,
            })
    total = len(benchmark["cases"])
    passed = total - len(failures)
    accuracy = passed / total if total else 0.0
    return {
        "version": benchmark["version"],
        "total": total,
        "passed": passed,
        "failed": len(failures),
        "accuracy": round(accuracy, 4),
        "minimum_accuracy": benchmark["minimum_accuracy"],
        "failures": failures,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["accuracy"] >= result["minimum_accuracy"] else 1)
