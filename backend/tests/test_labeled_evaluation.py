from evaluation.labeled import score_labels, validate_annotation


def test_label_scores_report_false_positives_and_false_negatives():
    score = score_labels(["事故认定书", "护理期限依据"], ["事故认定书", "收入证明"])
    assert score.true_positive == 1
    assert score.false_positive == 1
    assert score.false_negative == 1
    assert score.precision == 0.5
    assert score.recall == 0.5
    assert score.f1 == 0.5


def test_real_case_annotation_requires_authorization_deidentification_and_dual_review():
    record = {
        "schema_version": "1.0",
        "case_id": "case-local-id",
        "authorization_confirmed": True,
        "deidentification_confirmed": True,
        "annotator_id": "annotator-a",
        "reviewer_id": "lawyer-b",
        "status": "approved",
        "facts": [],
        "expected_missing_materials": [],
        "expected_conflicts": [],
        "expected_rule_hits": [],
        "mandatory_human_review_items": [],
    }
    assert validate_annotation(record) == []
    record["reviewer_id"] = "annotator-a"
    record["deidentification_confirmed"] = False
    errors = validate_annotation(record)
    assert any("脱敏" in error for error in errors)
    assert any("不同人员" in error for error in errors)
