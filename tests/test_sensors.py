# ============================================================
#  tests/test_sensors.py — Sensör Birim Testleri
# ============================================================

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.sensors import SensorEngine


def test_float_ratio_positive():
    """Float ratio daima pozitif olmalı."""
    assert SensorEngine.float_ratio(500_000, 10_000_000) > 0
    assert SensorEngine.float_ratio(-100_000, 10_000_000) == 0.0  # Negatif → 0
    assert SensorEngine.float_ratio(0, 0) == 0.0                  # Sıfır bölme
    print("✅ test_float_ratio_positive")


def test_cost_basis_gap():
    """Maliyet < Fiyat iken gap pozitif olmalı."""
    gap = SensorEngine.cost_basis_gap(100.0, 90.0)
    assert gap > 0, f"Beklenen > 0, alınan: {gap}"

    gap_neg = SensorEngine.cost_basis_gap(90.0, 100.0)
    assert gap_neg < 0, f"Beklenen < 0, alınan: {gap_neg}"
    print("✅ test_cost_basis_gap")


def test_absorption_velocity_increases():
    """Artan lot miktarıyla velocity artmalı."""
    engine = SensorEngine()
    now    = time.time()

    engine.absorption_velocity("THYAO", 100_000, now)
    engine.absorption_velocity("THYAO", 200_000, now + 5)
    v2 = engine.absorption_velocity("THYAO", 400_000, now + 10)

    assert v2 > 0, "Velocity sıfır olamaz!"
    print(f"✅ test_absorption_velocity_increases  |  Velocity={v2:.2f} lot/s")


def test_pressure_levels():
    """Maliyet baskısı seviyeleri doğru etiketlenmeli."""
    assert SensorEngine.cost_basis_pressure_level(100, 90)  == "LOW_PRESSURE"
    assert SensorEngine.cost_basis_pressure_level(100, 97)  == "CRITICAL_SUPPORT"
    assert SensorEngine.cost_basis_pressure_level(100, 102) == "UNDERWATER"
    assert SensorEngine.cost_basis_pressure_level(100, 120) == "HEAVY_LOSS"
    print("✅ test_pressure_levels")


if __name__ == "__main__":
    test_float_ratio_positive()
    test_cost_basis_gap()
    test_absorption_velocity_increases()
    test_pressure_levels()
    print("\n🟢 Tüm Sensör testleri geçti!")
