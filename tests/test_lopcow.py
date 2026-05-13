# ============================================================
#  tests/test_lopcow.py — LOPCOW Engine Unit Testleri
# ============================================================

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.lopcow import LOPCOWEngine


def _sample_matrix():
    return {
        "THYAO": {"volume": 2_500_000, "net_lot": 450_000, "float_ratio": 0.056,
                  "absorption_velocity": 1250.0, "cost_basis_gap": 0.053, "index_performance": 1.2},
        "ASELS": {"volume":   900_000, "net_lot": 120_000, "float_ratio": 0.021,
                  "absorption_velocity":  320.0, "cost_basis_gap": 0.010, "index_performance": 0.8},
        "GARAN": {"volume": 5_000_000, "net_lot": 800_000, "float_ratio": 0.092,
                  "absorption_velocity": 3100.0, "cost_basis_gap": 0.082, "index_performance": 2.1},
    }


def test_weights_sum_to_one():
    """Ağırlıkların toplamı 1.0 olmalı."""
    engine = LOPCOWEngine()
    result = engine.compute_weights(_sample_matrix())
    total  = sum(result["weights"].values())
    assert abs(total - 1.0) < 1e-4, f"Ağırlık toplamı: {total}"
    print(f"✅ test_weights_sum_to_one  |  Toplam: {total:.6f}")


def test_all_criteria_present():
    """Tüm kriterler için ağırlık üretilmeli."""
    engine  = LOPCOWEngine()
    result  = engine.compute_weights(_sample_matrix())
    missing = [c for c in LOPCOWEngine.CRITERIA if c not in result["weights"]]
    assert not missing, f"Eksik kriterler: {missing}"
    print(f"✅ test_all_criteria_present  |  Kriterler: {list(result['weights'].keys())}")


def test_normalization_bounds():
    """Normalize değerler 0-1 aralığında olmalı."""
    engine = LOPCOWEngine()
    result = engine.compute_weights(_sample_matrix())
    for ticker, row in result["normalized"].items():
        for crit, val in row.items():
            assert 0.0 <= val <= 1.0 + 1e-9, \
                f"{ticker}.{crit} = {val} sınır dışı!"
    print("✅ test_normalization_bounds  |  Tüm değerler 0-1 aralığında")


def test_empty_matrix():
    """Boş matris durumu çökmemeli."""
    engine = LOPCOWEngine()
    result = engine.compute_weights({})
    assert "weights" in result
    print("✅ test_empty_matrix  |  Boş matris güvenle işlendi")


if __name__ == "__main__":
    test_weights_sum_to_one()
    test_all_criteria_present()
    test_normalization_bounds()
    test_empty_matrix()
    print("\n🟢 Tüm LOPCOW testleri geçti!")
