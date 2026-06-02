"""``shopeedw`` command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from shopeedw import __version__

    print(f"shopee-product-scraper-warehouse {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from shopeedw.io_jsonl import dump_products, dump_shops
    from shopeedw.simulator import generate

    shops, products = generate(
        n_shops=args.shops,
        n_products=args.products,
        n_snapshots_per_product=args.snapshots,
        snapshot_interval_minutes=args.interval,
        seed=args.seed,
    )
    if args.output:
        out_dir = Path(args.output)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "shops.jsonl").write_text(dump_shops(shops), encoding="utf-8")
        (out_dir / "products.jsonl").write_text(dump_products(products), encoding="utf-8")
        print(
            f"wrote {len(shops)} shops + {len(products)} product snapshots to {out_dir}/",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(dump_products(products))
    return 0


def _load_warehouse(directory: Path):  # type: ignore[no-untyped-def]
    from shopeedw.io_jsonl import load_products, load_shops
    from shopeedw.warehouse import Warehouse

    wh = Warehouse()
    shops_path = directory / "shops.jsonl"
    products_path = directory / "products.jsonl"
    if shops_path.exists():
        for s in load_shops(shops_path.read_text(encoding="utf-8")):
            wh.ingest_shop(s)
    if products_path.exists():
        for p in load_products(products_path.read_text(encoding="utf-8")):
            wh.ingest_product(p)
    return wh


def cmd_top_sellers(args: argparse.Namespace) -> int:
    from shopeedw.aggregations import top_sellers_by_gmv, top_sellers_by_volume

    wh = _load_warehouse(Path(args.dataset))
    fn = top_sellers_by_gmv if args.by == "gmv" else top_sellers_by_volume
    rankings = fn(wh, n=args.n)
    print(f"{'shop_id':<10} {'gmv_vnd':>15} {'units':>8}  name")
    for r in rankings:
        print(f"{r.shop_id:<10} {r.total_gmv_vnd:>15,} {r.total_units_sold:>8,}  {r.shop_name}")
    return 0


def cmd_top_categories(args: argparse.Namespace) -> int:
    from shopeedw.aggregations import top_categories_by_gmv

    wh = _load_warehouse(Path(args.dataset))
    cats = top_categories_by_gmv(wh, n=args.n)
    print(f"{'category_key':<22} {'gmv_vnd':>15} {'units':>8} {'name_vn'}")
    for c in cats:
        print(
            f"{c.category_key:<22} {c.total_gmv_vnd:>15,} {c.total_units_sold:>8,} {c.category_name_vn}"
        )
    return 0


def cmd_price_drops(args: argparse.Namespace) -> int:
    from shopeedw.aggregations import price_drops

    wh = _load_warehouse(Path(args.dataset))
    drops = price_drops(wh, threshold_pct=args.threshold, min_history_points=args.min_history)
    print(
        f"found {len(drops)} drops over {args.threshold}% (min {args.min_history} history points)"
    )
    for d in drops[: args.n]:
        print(
            f"  item={d.item_id} shop={d.shop_id} drop={d.drop_pct:.1f}%  "
            f"{d.historical_max_vnd:,} → {d.current_price_vnd:,}  {d.name}"
        )
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from shopeedw.aggregations import summarise

    wh = _load_warehouse(Path(args.dataset))
    s = summarise(wh)
    payload = {
        "n_products": s.n_products,
        "n_shops": s.n_shops,
        "n_price_history_points": s.n_price_history_points,
        "total_gmv_vnd": s.total_gmv_vnd,
        "by_category": {
            k: {
                "n_products": v.n_products,
                "total_gmv_vnd": v.total_gmv_vnd,
                "total_units_sold": v.total_units_sold,
                "name_vn": v.category_name_vn,
            }
            for k, v in s.by_category.items()
        },
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="shopeedw",
        description="Shopee VN product warehouse + top-seller aggregations.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit synthetic shops + products as JSONL")
    sim.add_argument("--shops", type=int, default=20)
    sim.add_argument("--products", type=int, default=100)
    sim.add_argument("--snapshots", type=int, default=1)
    sim.add_argument("--interval", type=int, default=60, help="minutes between snapshots")
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument(
        "--output", default=None, help="directory to write shops.jsonl + products.jsonl"
    )
    sim.set_defaults(func=cmd_simulate)

    ts = sub.add_parser("top-sellers", help="rank shops by GMV or volume")
    ts.add_argument(
        "--dataset", required=True, help="directory containing shops.jsonl + products.jsonl"
    )
    ts.add_argument("--by", choices=["gmv", "volume"], default="gmv")
    ts.add_argument("--n", type=int, default=10)
    ts.set_defaults(func=cmd_top_sellers)

    tc = sub.add_parser("top-categories", help="rank categories by GMV")
    tc.add_argument("--dataset", required=True)
    tc.add_argument("--n", type=int, default=5)
    tc.set_defaults(func=cmd_top_categories)

    pd = sub.add_parser("price-drops", help="list products with significant price drops")
    pd.add_argument("--dataset", required=True)
    pd.add_argument("--threshold", type=float, default=20.0)
    pd.add_argument("--min-history", dest="min_history", type=int, default=3)
    pd.add_argument("--n", type=int, default=20)
    pd.set_defaults(func=cmd_price_drops)

    sm = sub.add_parser("summary", help="dump warehouse summary as JSON")
    sm.add_argument("--dataset", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
