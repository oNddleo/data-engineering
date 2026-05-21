# vn-shipping-pipeline

Vietnam domestic shipping fee calculator and pipeline.
Supports GHN, GHTK, J&T Express, Viettel Post, Vietnam Post.

## Features

- Weight-tier pricing (≤500g / ≤1kg / per-500g above 1kg)
- COD fee: flat 3,000 VND + 1% of COD amount
- Fragile surcharge: 5,000 VND
- Inner-city vs inter-province zones
- Standard / Express / Same-Day service tiers
- JSONL I/O, simulator, CLI

## Usage

```python
from vnship.pricing import calculate_fee
from vnship.schema import Carrier, ServiceType, ShipmentRequest, ZoneType

req = ShipmentRequest(
    carrier=Carrier.GHN,
    service=ServiceType.STANDARD,
    zone=ZoneType.INNER_CITY,
    weight_g=1500,
    declared_value_vnd=500_000,
    cod_amount_vnd=300_000,
    is_fragile=False,
)
result = calculate_fee(req)
print(result.total_fee_vnd)
```

## CLI

```bash
vnship carriers
vnship price --carrier GHN --weight-g 1500 --cod-amount 300000
vnship simulate --n 1000 --seed 42
```

## License

MIT
