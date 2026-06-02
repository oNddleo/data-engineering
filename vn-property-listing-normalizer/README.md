# vn-property-listing-normalizer

Parse free-text Vietnamese real-estate listings into structured records.

Listings on VN classifieds (batdongsan, chotot, alonhadat) are written in
prose: prices mixed `tỷ` / `triệu`, areas as `75m²` or `7x10m`
(frontage × depth), addresses prefixed with `Quận / Huyện / Phường / Xã /
TP. / Tỉnh`. This package extracts those fields deterministically — no
runtime dependencies, mypy `--strict` clean.

## What it does

* **Price** — `parse_price_vnd("2.5 tỷ")` → `2_500_000_000`. Handles
  `tỷ`, `triệu`, `nghìn`, `tr`, `k`, raw VND, and VN-locale numbers
  (`3,2 tỷ` with comma decimal, `5.500.000.000` with dot-grouped
  thousands).
* **Area** — `parse_area_m2("7x10m")` → `70`. Accepts plain `75m²`,
  `120 m2`, `7x10m` (frontage × depth), and `75.5 m²`.
* **Location** — `parse_province / parse_district / parse_ward` pull
  out the canonical labels using VN administrative prefixes.
* **Normalize** — `normalize(raw)` glues the above into a `Listing`
  dataclass with `price_per_m2_vnd` derived.

## Quick start

```bash
pip install vn-property-listing-normalizer
vnprop info
vnprop price "2.5 tỷ"
vnprop area "7x10m"
vnprop simulate --n 100 --seed 0 --output raw.jsonl
vnprop normalize --input raw.jsonl --output listings.jsonl
```

## Library

```python
from vnprop import normalize, RawListing

raw = RawListing(
    listing_id="L-001",
    title="Bán căn hộ 75m² tại Quận 7, TP. Hồ Chí Minh",
    description="Giá 3,2 tỷ, 2 phòng ngủ, 2 WC",
    price_text="3,2 tỷ",
    area_text="75m²",
)
listing = normalize(raw)
print(listing.price_per_m2_vnd)  # 42_666_667
```

## Design

* Zero runtime dependencies (stdlib only).
* Frozen-slots dataclasses with `__post_init__` validation.
* All parsers raise `ValueError` on malformed input — no silent zeros.
* Per-m² is derived (not stored) so the source-of-truth stays the
  amount + area pair.

## Development

```bash
make install   # pip install -e .[dev]
make test      # pytest
make lint      # ruff check + format
make typecheck # mypy --strict
```

## License

MIT.
