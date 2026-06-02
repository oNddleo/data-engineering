"""Synthetic raw-listing stream generator."""

from __future__ import annotations

import random

from vnprop.normalizer import RawListing

_TEMPLATES_HCMC = (
    ("Chung cư cao cấp Q.2", "Căn hộ 3 phòng ngủ tại {ward}, Quận 2, TP. Hồ Chí Minh"),
    ("Nhà phố Q.7", "Nhà phố mặt tiền {ward}, Quận 7, TP. Hồ Chí Minh"),
    ("Biệt thự Thảo Điền", "Biệt thự sân vườn Phường Thảo Điền, Quận 2, TP. Hồ Chí Minh"),
    ("Shophouse Q.1", "Shophouse mặt phố {ward}, Quận 1, TP. Hồ Chí Minh"),
    ("Đất nền Củ Chi", "Đất thổ cư tại Xã Tân Phú Trung, Huyện Củ Chi, TP. Hồ Chí Minh"),
)

_TEMPLATES_HANOI = (
    ("Chung cư Cầu Giấy", "Căn hộ 2PN tại Phường Dịch Vọng, Quận Cầu Giấy, Hà Nội"),
    ("Nhà phố Hoàn Kiếm", "Nhà phố mặt tiền Phường Hàng Bài, Quận Hoàn Kiếm, Hà Nội"),
    ("Biệt thự Ciputra", "Biệt thự khu Tây Hồ Tây, Quận Tây Hồ, Hà Nội"),
)


def generate(n: int = 30, seed: int = 0) -> list[RawListing]:
    """Generate ``n`` synthetic VN listings as raw free-text records."""
    if n < 0:
        raise ValueError("n must be >= 0")
    rng = random.Random(seed)
    templates = _TEMPLATES_HCMC + _TEMPLATES_HANOI
    wards = ("An Phú", "Bình Trưng Tây", "Thảo Điền", "Tân Phong", "Bến Nghé")
    out: list[RawListing] = []
    for i in range(n):
        title, desc_tpl = rng.choice(templates)
        desc = desc_tpl.format(ward=rng.choice(wards))
        area_m2 = rng.choice([50, 65, 80, 95, 120, 150, 200, 300])
        # Price varies by kind keyword in title.
        if "biệt thự" in title.lower():
            price = rng.uniform(15, 50)
            price_text = f"{price:.1f} tỷ"
        elif "đất" in title.lower():
            price = rng.uniform(2, 15)
            price_text = f"{price:.1f} tỷ"
        else:
            price = rng.uniform(2, 12)
            price_text = f"{price:.1f} tỷ"
        bedrooms = rng.choice([2, 3, 4])
        full_desc = (
            f"{desc}. Diện tích {area_m2}m². {bedrooms} phòng ngủ, " f"2 WC. Giá {price_text}."
        )
        out.append(
            RawListing(
                listing_id=f"L-{i:06d}",
                title=title,
                description=full_desc,
                price_text=price_text,
                area_text=f"{area_m2}m²",
            )
        )
    return out


__all__ = ["generate"]
