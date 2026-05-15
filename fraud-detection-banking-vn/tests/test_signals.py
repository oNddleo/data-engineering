"""Per-signal detector tests."""

from __future__ import annotations

from datetime import datetime

from fraudvn.schema import VN_TZ
from fraudvn.signals import (
    signal_beneficiary_hot,
    signal_blacklist_beneficiary,
    signal_keyword,
    signal_new_beneficiary_large,
    signal_night_transfer,
    signal_otp_race,
    signal_round_amount_below,
    signal_velocity_burst,
)
from fraudvn.state import AccountState

from ._fixtures import make_req, t_at

# ---------------------------------------------------------------------------
# Keyword.


def test_keyword_clean_narrative_no_hits():
    assert signal_keyword(make_req(narrative="tien an trua")) == []


def test_keyword_cong_an_fires():
    hits = signal_keyword(make_req(narrative="Yêu cầu Công An điều tra"))
    assert any(h.name == "KEYWORD_CONG_AN_IMPERSONATION" for h in hits)


def test_keyword_multiple_categories_each_fire():
    hits = signal_keyword(make_req(narrative="Đầu tư crypto vay tiền online"))
    names = {h.name for h in hits}
    assert "KEYWORD_CRYPTO_FOREX_SCAM" in names
    assert "KEYWORD_LOAN_SCAM" in names


# ---------------------------------------------------------------------------
# Blacklist beneficiary.


def test_blacklist_hit_fires():
    hits = signal_blacklist_beneficiary(
        make_req(beneficiary="BAD-001"), blacklist=frozenset({"BAD-001"})
    )
    assert len(hits) == 1
    assert hits[0].name == "BLACKLIST_BENEFICIARY"
    assert hits[0].points == 100


def test_blacklist_miss_no_alert():
    assert signal_blacklist_beneficiary(make_req(beneficiary="OK"), blacklist=frozenset()) == []


# ---------------------------------------------------------------------------
# New beneficiary + large amount.


def test_new_beneficiary_large_fires():
    st = AccountState(account_id="A")
    hits = signal_new_beneficiary_large(make_req(beneficiary="NEW", amount=6_000_000), src_state=st)
    assert hits and hits[0].name == "NEW_BENEFICIARY_LARGE"


def test_new_beneficiary_small_amount_no_alert():
    st = AccountState(account_id="A")
    assert (
        signal_new_beneficiary_large(make_req(beneficiary="NEW", amount=100_000), src_state=st)
        == []
    )


def test_known_beneficiary_no_alert():
    st = AccountState(account_id="A")
    st.prior_beneficiaries.add("KNOWN")
    assert (
        signal_new_beneficiary_large(make_req(beneficiary="KNOWN", amount=50_000_000), src_state=st)
        == []
    )


# ---------------------------------------------------------------------------
# Night transfer.


def test_night_transfer_fires_at_2am():
    req = make_req(occurred_at=datetime(2026, 5, 14, 2, 30, tzinfo=VN_TZ))
    hits = signal_night_transfer(req)
    assert hits and hits[0].name == "NIGHT_TRANSFER"


def test_night_transfer_fires_at_23h():
    req = make_req(occurred_at=datetime(2026, 5, 14, 23, 30, tzinfo=VN_TZ))
    assert signal_night_transfer(req)


def test_day_transfer_no_alert():
    req = make_req(occurred_at=datetime(2026, 5, 14, 14, 0, tzinfo=VN_TZ))
    assert signal_night_transfer(req) == []


def test_boundary_at_5am_no_alert():
    """05:00 is the start of the day window."""
    req = make_req(occurred_at=datetime(2026, 5, 14, 5, 0, tzinfo=VN_TZ))
    assert signal_night_transfer(req) == []


# ---------------------------------------------------------------------------
# OTP race.


def test_otp_race_fast_fires():
    req = make_req(otp_delta_seconds=2.0)
    hits = signal_otp_race(req)
    assert hits and hits[0].name == "OTP_RACE"


def test_otp_race_slow_no_alert():
    req = make_req(otp_delta_seconds=20.0)
    assert signal_otp_race(req) == []


def test_otp_race_no_otp_no_alert():
    req = make_req(otp_delta_seconds=None)
    assert signal_otp_race(req) == []


# ---------------------------------------------------------------------------
# Round amount below 10M.


def test_round_amount_below_fires():
    assert signal_round_amount_below(make_req(amount=9_800_000))


def test_round_amount_at_threshold_fires():
    assert signal_round_amount_below(make_req(amount=10_000_000))


def test_round_amount_just_below_band_low_no_alert():
    assert signal_round_amount_below(make_req(amount=9_500_000)) == []


def test_round_amount_above_threshold_no_alert():
    assert signal_round_amount_below(make_req(amount=10_500_000)) == []


def test_small_amount_no_alert():
    assert signal_round_amount_below(make_req(amount=500_000)) == []


# ---------------------------------------------------------------------------
# Velocity burst.


def test_velocity_burst_fires():
    st = AccountState(account_id="A")
    for i in range(6):
        st.recent_outgoing.append((f"B-{i}", t_at(i * 30)))
    hits = signal_velocity_burst(make_req(occurred_at=t_at(180)), src_state=st)
    assert hits and hits[0].name == "VELOCITY_BURST"


def test_velocity_burst_threshold_not_reached_no_alert():
    st = AccountState(account_id="A")
    for i in range(3):
        st.recent_outgoing.append((f"B-{i}", t_at(i * 30)))
    assert signal_velocity_burst(make_req(occurred_at=t_at(120)), src_state=st) == []


def test_velocity_burst_old_entries_evicted_by_time():
    """Outgoing txns older than VELOCITY_BURST_WINDOW_SECONDS shouldn't count."""
    st = AccountState(account_id="A")
    # 6 outgoings spaced 10 minutes apart → only the last 5min worth count.
    for i in range(6):
        st.recent_outgoing.append((f"B-{i}", t_at(i * 600)))
    assert signal_velocity_burst(make_req(occurred_at=t_at(3600)), src_state=st) == []


# ---------------------------------------------------------------------------
# Beneficiary hot.


def test_beneficiary_hot_fires_with_many_sources():
    st = AccountState(account_id="D")
    for i in range(5):
        st.recent_incoming_sources.append((f"S-{i}", t_at(i * 60)))
    hits = signal_beneficiary_hot(make_req(occurred_at=t_at(120)), dst_state=st)
    assert hits and hits[0].name == "BENEFICIARY_HOT"


def test_beneficiary_hot_repeated_source_does_not_count_twice():
    st = AccountState(account_id="D")
    for i in range(10):
        st.recent_incoming_sources.append(("SAME", t_at(i * 30)))
    assert signal_beneficiary_hot(make_req(occurred_at=t_at(60)), dst_state=st) == []


def test_beneficiary_hot_window_eviction():
    st = AccountState(account_id="D")
    for i in range(5):
        st.recent_incoming_sources.append((f"S-{i}", t_at(i * 10_000)))
    # Latest at 40_000s; check at 50_000s. Window is 3600s → only the last entry.
    assert signal_beneficiary_hot(make_req(occurred_at=t_at(50_000)), dst_state=st) == []
