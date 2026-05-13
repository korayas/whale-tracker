# ============================================================
#  pipeline/index_monitor.py
#  Hissenin ait olduğu sektörel endeksin anlık performansını
#  takip eder ve korelasyon analizi yapar.
# ============================================================

import logging
import statistics
from collections import deque
from typing import Optional
from config import SECTOR_INDEX_MAP, GATEKEEPER

logger = logging.getLogger(__name__)

# Endeks geçmiş penceresi için periyot sayısı
_LOOKBACK = GATEKEEPER["sector_check"]["lookback_minutes"]


class IndexMonitor:
    """
    Her hisse için:
      - Endeks anlık performansı (% değişim)
      - Geçmiş fiyat serisi (rolling buffer)
      - Pearson korelasyon katsayısı
    hesaplar.
    """

    def __init__(self):
        # {ticker: deque([float, ...])}  → son N periyot hisse fiyatı
        self._price_history: dict[str, deque] = {}
        # {index_code: deque([float, ...])} → son N periyot endeks kapanışı
        self._index_history: dict[str, deque] = {}

    # ----------------------------------------------------------
    # Güncelleme
    # ----------------------------------------------------------

    def update(self, ticker: str, price: float, index_perf: float):
        """
        Her döngüde yeni fiyat ve endeks performansını buffer'a ekler.
        """
        # Hisse fiyatı
        if ticker not in self._price_history:
            self._price_history[ticker] = deque(maxlen=_LOOKBACK)
        self._price_history[ticker].append(price)

        # Endeks performansı
        idx_code = SECTOR_INDEX_MAP.get(ticker, "XUTUM")
        if idx_code not in self._index_history:
            self._index_history[idx_code] = deque(maxlen=_LOOKBACK)
        self._index_history[idx_code].append(index_perf)

    def update_all(self, raw_data: dict):
        """fetch_all() çıktısını toplu günceller."""
        for ticker, data in raw_data.items():
            self.update(
                ticker,
                price      = data.get("price", 0),
                index_perf = data.get("index_perf", 0),
            )

    # ----------------------------------------------------------
    # Analiz
    # ----------------------------------------------------------

    def get_index_performance(self, ticker: str) -> float:
        """
        Hissenin endeksinin son periyottaki % performansını döner.
        """
        idx_code = SECTOR_INDEX_MAP.get(ticker, "XUTUM")
        history  = self._index_history.get(idx_code, deque())
        if not history:
            return 0.0
        return history[-1]  # En son değer

    def get_correlation(self, ticker: str) -> float:
        """
        Hisse fiyatı ile sektörel endeks arasındaki
        Pearson korelasyon katsayısını hesaplar (r).

        Yeterli veri yoksa 0.0 döner.
        """
        idx_code     = SECTOR_INDEX_MAP.get(ticker, "XUTUM")
        price_series = list(self._price_history.get(ticker, []))
        index_series = list(self._index_history.get(idx_code, []))

        n = min(len(price_series), len(index_series))
        if n < 5:
            logger.debug(f"[IndexMonitor] {ticker} için yeterli veri yok (n={n})")
            return 0.0

        price_series = price_series[-n:]
        index_series = index_series[-n:]

        return self._pearson(price_series, index_series)

    def has_sector_support(self, ticker: str) -> bool:
        """
        Endeks desteği var mı?
        Pearson r >= config'deki min_correlation eşiği.
        """
        min_r = GATEKEEPER["sector_check"]["min_correlation"]
        r     = self.get_correlation(ticker)
        return r >= min_r

    # ----------------------------------------------------------
    # İstatistik Yardımcıları
    # ----------------------------------------------------------

    @staticmethod
    def _pearson(x: list, y: list) -> float:
        """Pearson korelasyon katsayısını hesaplar."""
        n  = len(x)
        if n < 2:
            return 0.0

        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        numerator   = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denom_x     = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
        denom_y     = sum((yi - mean_y) ** 2 for yi in y) ** 0.5
        denominator = denom_x * denom_y

        if denominator == 0:
            return 0.0

        return round(numerator / denominator, 4)

    def get_summary(self, ticker: str) -> dict:
        """Hisse için tam endeks özeti döner."""
        return {
            "index_code":        SECTOR_INDEX_MAP.get(ticker, "XUTUM"),
            "index_performance": self.get_index_performance(ticker),
            "correlation":       self.get_correlation(ticker),
            "has_support":       self.has_sector_support(ticker),
        }
