# ============================================================
#  gatekeeper/zscore_filter.py
#  Z-Score Hacim Kontrolü:
#  Anormal hacim artışlarını matematiksel olarak doğrular.
#  Z > eşik → Gerçek balina hareketi
#  Z < eşik → Normal seyir, sinyal üretme
# ============================================================

import math
import logging
from collections import defaultdict, deque
from config import GATEKEEPER

logger = logging.getLogger(__name__)

_THRESHOLD = GATEKEEPER["zscore_volume"]["threshold"]
_LOOKBACK  = GATEKEEPER["zscore_volume"]["lookback_periods"]


class ZScoreFilter:
    """
    Hacim Z-Score Filtresi:

    Z = (Hacim - μ) / σ

    μ : Son _LOOKBACK periyot hacim ortalaması
    σ : Standart sapma
    Z > _THRESHOLD → Anormal → Balina onaylandı
    Z ≤ _THRESHOLD → Normal seyir → Sinyal üretme
    """

    def __init__(self):
        # {ticker: deque([volume, ...])} hacim geçmişi
        self._volume_history: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=_LOOKBACK)
        )

    # ----------------------------------------------------------
    # Güncelleme
    # ----------------------------------------------------------

    def update(self, ticker: str, volume: float):
        """Yeni hacim değerini geçmişe ekler."""
        self._volume_history[ticker].append(volume)

    def update_all(self, raw_data: dict):
        """Tüm hisseler için toplu güncelleme."""
        for ticker, data in raw_data.items():
            self.update(ticker, data.get("volume", 0))

    # ----------------------------------------------------------
    # Z-Score Hesaplama
    # ----------------------------------------------------------

    def compute_zscore(self, ticker: str, current_volume: float) -> float:
        """
        Mevcut hacmin tarihsel dağılım içindeki Z-Score'unu hesaplar.

        Yeterli veri yoksa (< 3 periyot) 0.0 döner.
        """
        history = list(self._volume_history[ticker])

        if len(history) < 3:
            logger.debug(f"[ZScore] {ticker} için yetersiz veri ({len(history)} periyot)")
            return 0.0

        mean = sum(history) / len(history)
        variance = sum((v - mean) ** 2 for v in history) / len(history)
        std_dev  = math.sqrt(variance)

        if std_dev == 0:
            return 0.0

        z = (current_volume - mean) / std_dev
        return round(z, 4)

    # ----------------------------------------------------------
    # Filtre Kontrolü
    # ----------------------------------------------------------

    def is_abnormal(self, ticker: str, current_volume: float) -> bool:
        """
        Z-Score > eşik değeri mi?
        True → Anormal hacim → Sinyal üretilebilir
        False → Normal hacim → Sinyal üretme
        """
        z = self.compute_zscore(ticker, current_volume)
        return z >= _THRESHOLD

    def check(self, ticker: str, current_volume: float) -> dict:
        """
        Tam Z-Score kontrol raporu döner.

        {
            "passed":         bool,
            "z_score":        float,
            "threshold":      float,
            "mean_volume":    float,
            "std_volume":     float,
            "current_volume": float,
            "verdict":        str,
        }
        """
        history = list(self._volume_history[ticker])
        n = len(history)

        if n < 3:
            return {
                "passed":         True,   # Veri yoksa filtre geçilir
                "z_score":        0.0,
                "threshold":      _THRESHOLD,
                "mean_volume":    0.0,
                "std_volume":     0.0,
                "current_volume": current_volume,
                "verdict":        "INSUFFICIENT_DATA",
            }

        mean    = sum(history) / n
        std_dev = math.sqrt(sum((v - mean) ** 2 for v in history) / n)
        z       = self.compute_zscore(ticker, current_volume)
        passed  = z >= _THRESHOLD

        verdict = "ABNORMAL_VOLUME" if passed else "NORMAL_VOLUME"

        logger.debug(
            f"[ZScore] {ticker} → Z={z:.2f}  "
            f"(μ={mean:.0f}, σ={std_dev:.0f})  "
            f"→ {verdict}"
        )

        return {
            "passed":         passed,
            "z_score":        z,
            "threshold":      _THRESHOLD,
            "mean_volume":    round(mean, 2),
            "std_volume":     round(std_dev, 2),
            "current_volume": current_volume,
            "verdict":        verdict,
        }

    # ----------------------------------------------------------
    # Toplu Kontrol
    # ----------------------------------------------------------

    def check_all(self, raw_data: dict) -> dict:
        """
        Tüm hisseler için Z-Score kontrolü uygular.
        Döner: { "THYAO": {check_result}, ... }
        """
        results = {}
        for ticker, data in raw_data.items():
            volume = data.get("volume", 0)
            results[ticker] = self.check(ticker, volume)
        return results

    # ----------------------------------------------------------
    # Yardımcı: Hacim Yüzdelik
    # ----------------------------------------------------------

    def get_volume_percentile(self, ticker: str, current_volume: float) -> float:
        """
        Mevcut hacmin tarihsel dağılımdaki yüzdelik dilimini döner.
        100 → Tarihsel rekor  |  50 → Medyan seviyesi
        """
        history = list(self._volume_history[ticker])
        if not history:
            return 50.0

        below = sum(1 for v in history if v <= current_volume)
        return round((below / len(history)) * 100, 1)
