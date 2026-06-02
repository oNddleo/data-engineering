"""CLI smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shopeedw.cli import main


def test_cli_info(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "shopee-product-scraper-warehouse" in out


def test_cli_simulate_to_dir(tmp_path: Path):
    out_dir = tmp_path / "data"
    rc = main(
        ["simulate", "--shops", "5", "--products", "10", "--seed", "1", "--output", str(out_dir)]
    )
    assert rc == 0
    assert (out_dir / "shops.jsonl").exists()
    assert (out_dir / "products.jsonl").exists()


def test_cli_top_sellers_gmv(tmp_path: Path, capsys):
    out_dir = tmp_path / "data"
    main(["simulate", "--shops", "5", "--products", "20", "--seed", "1", "--output", str(out_dir)])
    rc = main(["top-sellers", "--dataset", str(out_dir), "--by", "gmv", "--n", "3"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "shop_id" in out
    assert "gmv_vnd" in out


def test_cli_top_sellers_volume(tmp_path: Path, capsys):
    out_dir = tmp_path / "data"
    main(["simulate", "--shops", "5", "--products", "20", "--seed", "1", "--output", str(out_dir)])
    rc = main(["top-sellers", "--dataset", str(out_dir), "--by", "volume", "--n", "3"])
    assert rc == 0


def test_cli_top_categories(tmp_path: Path, capsys):
    out_dir = tmp_path / "data"
    main(["simulate", "--shops", "5", "--products", "20", "--seed", "1", "--output", str(out_dir)])
    rc = main(["top-categories", "--dataset", str(out_dir), "--n", "3"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "category_key" in out


def test_cli_price_drops_with_multi_snapshot(tmp_path: Path, capsys):
    out_dir = tmp_path / "data"
    main(
        [
            "simulate",
            "--shops",
            "3",
            "--products",
            "10",
            "--snapshots",
            "5",
            "--seed",
            "1",
            "--output",
            str(out_dir),
        ]
    )
    rc = main(["price-drops", "--dataset", str(out_dir), "--threshold", "10"])
    assert rc == 0


def test_cli_summary_json(tmp_path: Path, capsys):
    out_dir = tmp_path / "data"
    main(["simulate", "--shops", "3", "--products", "8", "--seed", "1", "--output", str(out_dir)])
    rc = main(["summary", "--dataset", str(out_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["n_shops"] == 3
    assert payload["n_products"] == 8


def test_cli_no_subcommand_errors():
    with pytest.raises(SystemExit):
        main([])
