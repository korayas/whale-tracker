# ============================================================
#  tests/test_alpas.py — ALPAS Engine Unit Testleri
# ============================================================

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.alpas  import ALPASEngine
from engine.lopcow import LOPCOWEngine


def _get_normalized_and_weights():
    matrix = {
        "THYAO": {"volume": 2_500_000, "net_lot": 450_000, "float_ratio": 0.056,
                  "absorption_velocity": 1250.0, "cost_basis_gap": 0.053, "index_performance": 1.2},
        "ASELS": {"volume":   900_000, "net_lot": 120_000, "float_ratio": 0.021,
                  "absorption_velocity":  320.0, "cost_basis_gap": 0.010, "index_performance": 0.8},
        "GARAN": {"volume": 5_000_000, "net_lot": 800_000, "float_ratio": 0.092,
                  "absorption_velocity": 3100.0, "cost_basis_gap": 0.082, "index_performance": 2.1},
    }
    lopcow = LOPCOWEngine()
    result = lopcow.compute_weights(matrix)
    return result["normalized"], result["weights"]


def test_scores_in_range():
    """Tüm ALPAS skorları 0-1 arasında olmalı."""
    normalized, weights = _get_normalized_and_weights()
    engine  = ALPASEngine()
    results = engine.score(normalized, weights)
    for ticker, r in results.items():
        s = r["alpas_score"]
        assert 0.0 <= s <= 1.0, f"{ticker} skoru sınır dışı: {s}"
    print(f"✅ test_scores_in_range  |  {list(results.keys())}")


def test_ranks_are_unique():
    """Her hissenin benzersiz sıralaması olmalı."""
    normalized, weights = _get_normalized_and_weights()
    engine  = ALPASEngine()
    results = engine.score(normalized, weights)
    ranks   = [r["rank"] for r in results.values()]
    assert len(ranks) == len(set(ranks)), f"Tekrar eden sıralama: {ranks}"
    print(f"✅ test_ranks_are_unique  |  Sıralamalar: {ranks}")


def test_best_ticker_has_rank_1():
    """En yüksek ALPAS skoruna sahip hissenin rank=1 olmalı."""
    normalized, weights = _get_normalized_and_weights()
    engine  = ALPASEngine()
    results = engine.score(normalized, weights)
    best    = max(results.items(), key=lambda x: x[1]["alpas_score"])
    assert best[1]["rank"] == 1, f"En iyi hisse rank={best[1]['rank']}"
    print(f"✅ test_best_ticker_has_rank_1  |  En iyi: {best[0]}")


def test_explanation_generated():
    """Açıklama metni boş olmamalı."""
    normalized, weights = _get_normalized_and_weights()
    engine  = ALPASEngine()
    results = engine.score(normalized, weights)
    ticker  = list(results.keys())[0]
    expl    = ALPASEngine.build_explanation(ticker, results[ticker], weights)
    assert len(expl) > 10, "Açıklama çok kısa!"
    print(f"✅ test_explanation_generated  |  {len(expl)} karakter")


if __name__ == "__main__":
    test_scores_in_range()
    test_ranks_are_unique()
    test_best_ticker_has_rank_1()
    test_explanation_generated()
    print("\n🟢 Tüm ALPAS testleri geçti!")
