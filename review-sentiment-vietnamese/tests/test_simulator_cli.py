"""Simulator + CLI tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentvn.classifier import LexiconClassifier
from sentvn.cli import main
from sentvn.schema import SentimentLabel
from sentvn.simulator import generate


def test_generate_reproducible():
    a = generate(seed=42)
    b = generate(seed=42)
    assert [r.review_id for r in a] == [r.review_id for r in b]


def test_generate_count():
    rs = generate(seed=0, n_reviews=50)
    assert len(rs) == 50


def test_generate_classifies_into_three_labels():
    rs = generate(
        seed=0, n_reviews=100, pct_positive=0.5, pct_negative=0.3, pct_negated_positive=0.1
    )
    clf = LexiconClassifier()
    labels = {clf.classify(r).label for r in rs}
    # We'd expect all three to appear given the mix.
    assert SentimentLabel.POSITIVE in labels


def test_generate_rejects_bad_percentages():
    with pytest.raises(ValueError):
        generate(pct_positive=0.6, pct_negative=0.5, pct_negated_positive=0.1)


def test_cli_info(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "review-sentiment-vietnamese" in out


def test_cli_classify_inline(capsys):
    rc = main(["classify", "--text", "Sản phẩm rất tốt"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "POSITIVE" in out


def test_cli_classify_negated(capsys):
    rc = main(["classify", "--text", "Không tốt"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "NEGATIVE" in out


def test_cli_classify_empty_input_errors(capsys):
    rc = main(["classify", "--text", ""])
    assert rc == 2


def test_cli_simulate_to_file(tmp_path: Path):
    out = tmp_path / "reviews.jsonl"
    rc = main(["simulate", "--reviews", "10", "--seed", "1", "--output", str(out)])
    assert rc == 0
    lines = [line for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 10


def test_cli_analyse_writes_results(tmp_path: Path):
    reviews_path = tmp_path / "reviews.jsonl"
    results_path = tmp_path / "results.jsonl"
    main(["simulate", "--reviews", "20", "--seed", "1", "--output", str(reviews_path)])
    rc = main(["analyse", "--input", str(reviews_path), "--output", str(results_path)])
    assert rc == 0
    lines = [line for line in results_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 20


def test_cli_aggregate_seller(tmp_path: Path, capsys):
    reviews_path = tmp_path / "reviews.jsonl"
    results_path = tmp_path / "results.jsonl"
    main(["simulate", "--reviews", "40", "--seed", "1", "--output", str(reviews_path)])
    main(["analyse", "--input", str(reviews_path), "--output", str(results_path)])
    rc = main(
        [
            "aggregate",
            "--reviews",
            str(reviews_path),
            "--results",
            str(results_path),
            "--by",
            "seller",
            "--n",
            "5",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "key" in out
    assert "npp%" in out


def test_cli_aggregate_worst(tmp_path: Path, capsys):
    reviews_path = tmp_path / "reviews.jsonl"
    results_path = tmp_path / "results.jsonl"
    main(["simulate", "--reviews", "30", "--seed", "1", "--output", str(reviews_path)])
    main(["analyse", "--input", str(reviews_path), "--output", str(results_path)])
    rc = main(
        [
            "aggregate",
            "--reviews",
            str(reviews_path),
            "--results",
            str(results_path),
            "--by",
            "category",
            "--n",
            "3",
            "--worst",
        ]
    )
    assert rc == 0


def test_cli_summary(tmp_path: Path, capsys):
    import json

    reviews_path = tmp_path / "reviews.jsonl"
    results_path = tmp_path / "results.jsonl"
    main(["simulate", "--reviews", "20", "--seed", "1", "--output", str(reviews_path)])
    main(["analyse", "--input", str(reviews_path), "--output", str(results_path)])
    rc = main(["summary", "--results", str(results_path)])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["n_results"] == 20


def test_cli_no_subcommand_errors():
    with pytest.raises(SystemExit):
        main([])
