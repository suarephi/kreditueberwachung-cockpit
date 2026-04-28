"""Reference data sanity."""
from kreditueberwachung_mock import reference


def test_cantons_are_26():
    df = reference.cantons()
    assert len(df) == 26
    assert set(df["canton_code"]).issuperset({"ZH", "BE", "VD", "GE", "TI", "LU"})


def test_postal_codes_have_canton():
    plz = reference.postal_codes()
    cantons = set(reference.cantons()["canton_code"])
    assert plz["canton_code"].isin(cantons).all()
    assert plz["postal_code"].astype(str).str.len().between(4, 4).all()
