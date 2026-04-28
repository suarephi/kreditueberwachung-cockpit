import numpy as np
from kreditueberwachung_mock.loan import _sample_ltv, required_amortization


def test_ltv_distribution():
    rng = np.random.default_rng(1)
    samples = np.array([_sample_ltv(rng) for _ in range(20_000)])
    bulk = ((samples >= 60) & (samples <= 80)).mean()
    underwater = (samples > 100).mean()
    assert 0.55 < bulk < 0.75, bulk
    assert underwater < 0.02, underwater
    assert samples.min() >= 30
    assert samples.max() <= 110


def test_required_amortization_zero_when_below_target():
    # 60% LTV, no second mortgage → amort required = 0
    annual = required_amortization(loan_amount=600_000, market_value=1_000_000, second_amount=0)
    assert annual == 0.0


def test_required_amortization_pos_when_above_target():
    # 80% LTV with second mortgage portion → amort > 0
    annual = required_amortization(loan_amount=800_000, market_value=1_000_000, second_amount=130_000)
    assert annual > 0
