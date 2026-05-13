# ============================================================
#  engine/sensors.py
#  Analitik Metrikler ve Sensörler:
#    1. Float Ratio    — Tahta Hakimiyeti
#    2. Velocity of Absorption — Emir Hızı
#    3. Cost-Basis Analysis    — Maliyet Baskı Analizi
# ============================================================

import time
import logging
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)

# Velocity hesabı için lot geçmişi (saniye cinsinden)
_VELOCITY_WINDOW = 30   # Son 30 saniyeyi dikkate al


class SensorEngine:
    """
    Her hisse için 3 analitik sensörü hesaplar ve günceller.
    """

    def __init__(self):
        # Velocity hesabı için geçmiş {ticker: deque([(timestamp, net_lot), ...])}
        self._lot_history: dict[str, deque] = {}

    # ----------------------------------------------------------
    # Toplu Hesaplama (Her döngüde çağrılır)
    # ----------------------------------------------------------

    def compute_all(self, raw_data: dict, akd_metrics: dict) -> dict:
        """
        Tüm hisseler için 3 sensör metriğini hesaplar.

        Döner:
        {
            "THYAO": {
                "float_ratio":         0.056,
                "absorption_velocity": 1250.5,
                "cost_basis_gap":      0.053,
            },
            ...
        }
        """
        results = {}
        now = time.time()

        for ticker in raw_data:
            raw = raw_data[ticker]
            akd = akd_metrics.get(ticker, {})

            net_lot    = akd.get("net_lot", 0)
            float_lots = raw.get("float_lots", 1)
            price      = raw.get("price", 0)
            cost_basis = akd.get("cost_basis", price)

            float_ratio = self.float_ratio(net_lot, float_lots)
            velocity    = self.absorption_velocity(ticker, net_lot, now)
            cbg         = self.cost_basis_gap(price, cost_basis)

            results[ticker] = {
                "float_ratio":         float_ratio,
                "absorption_velocity": velocity,
                "cost_basis_gap":      cbg,
            }

            logger.debug(
                f"[Sensors] {ticker} → FR={float_ratio:.4f}  "
                f"Vel={velocity:.1f}  CBG={cbg:.4f}"
            )

        return results

    # ----------------------------------------------------------
    # Sensör 1: Float Ratio (Süpürme / Tahta Hakimiyeti)
    # ----------------------------------------------------------

    @staticmethod
    def float_ratio(net_lot: float, float_lots: float) -> float:
        """
        Float Ratio = Net Lot / Fiili Dolaşım

        Yorumlama:
          > 0.05  → Güçlü kurum hakimiyeti
          > 0.10  → Çok güçlü / birikim süreci
          < 0.01  → Zayıf / dağınık piyasa
        """
        if float_lots <= 0:
            return 0.0
        ratio = net_lot / float_lots
        return round(max(ratio, 0.0), 6)   # Negatif alım olmaz

    # ----------------------------------------------------------
    # Sensör 2: Velocity of Absorption (Emir Hızı)
    # ----------------------------------------------------------

    def absorption_velocity(self, ticker: str, net_lot: float,
                             timestamp: Optional[float] = None) -> float:
        """
        Emir Hızı = ΔLot / Δt  (lot/saniye)

        Son _VELOCITY_WINDOW saniye içindeki lot değişiminin
        ortalama hızını döner.

        Yüksek velocity → Büyük emirler hızla dolduruluyor → Güçlü balina.
        """
        now = timestamp or time.time()

        if ticker not in self._lot_history:
            self._lot_history[ticker] = deque()

        # Yeni gözlemi ekle
        self._lot_history[ticker].append((now, net_lot))

        # Pencere dışındaki eski gözlemleri temizle
        cutoff = now - _VELOCITY_WINDOW
        while self._lot_history[ticker] and self._lot_history[ticker][0][0] < cutoff:
            self._lot_history[ticker].popleft()

        history = list(self._lot_history[ticker])
        if len(history) < 2:
            return 0.0

        # İlk ve son gözlem arasındaki değişim
        t0, lot0 = history[0]
        t1, lot1 = history[-1]
        delta_t  = t1 - t0

        if delta_t == 0:
            return 0.0

        velocity = abs(lot1 - lot0) / delta_t
        return round(velocity, 2)

    # ----------------------------------------------------------
    # Sensör 3: Cost-Basis Analysis (Maliyet Baskısı)
    # ----------------------------------------------------------

    @staticmethod
    def cost_basis_gap(price: float, cost_basis: float) -> float:
        """
        Cost-Basis Gap = (Fiyat - Maliyet) / Fiyat

        Pozitif → Kurum karda → Alım devam edebilir
        Negatif → Kurum zararda → Satış baskısı riski
        Sıfıra yakın → Kritik maliyet desteği bölgesi
        """
        if price <= 0:
            return 0.0
        gap = (price - cost_basis) / price
        return round(gap, 6)

    @staticmethod
    def cost_basis_pressure_level(price: float, cost_basis: float) -> str:
        """
        Maliyet baskısı seviyesini etiketler.
        """
        gap = (price - cost_basis) / price if price > 0 else 0

        if gap > 0.05:
            return "LOW_PRESSURE"      # Rahat bölge
        elif 0 < gap <= 0.05:
            return "CRITICAL_SUPPORT"  # Maliyet yakınında
        elif -0.05 <= gap <= 0:
            return "UNDERWATER"        # Hafif zararda
        else:
            return "HEAVY_LOSS"        # Ağır zarar

    # ----------------------------------------------------------
    # Özet Raporu
    # ----------------------------------------------------------

    @staticmethod
    def get_summary(ticker: str, metrics: dict) -> str:
        """Sensör metriklerinin okunabilir özetini döner."""
        fr  = metrics.get("float_ratio", 0) * 100
        vel = metrics.get("absorption_velocity", 0)
        cbg = metrics.get("cost_basis_gap", 0) * 100

        return (
            f"[{ticker}] "
            f"FloatRatio={fr:.2f}%  "
            f"Velocity={vel:.1f}lot/s  "
            f"CostGap={cbg:+.2f}%"
        )
