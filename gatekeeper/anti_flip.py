# ============================================================
#  gatekeeper/anti_flip.py
#  Anti-Flipping Süzgeci:
#  Alıcı kurumun "günlükçü" mü yoksa "kalıcı" mı olduğunu
#  geçmiş işlem karakterine göre belirler.
# ============================================================

import logging
from collections import defaultdict, deque
from config import GATEKEEPER

logger = logging.getLogger(__name__)

_LOOKBACK  = GATEKEEPER["anti_flip"]["lookback_days"]
_MIN_RATIO = GATEKEEPER["anti_flip"]["consistency_ratio"]


class AntiFlipFilter:
    """
    Her hisse için kurumsal yön tutarlılığını izler.

    Mantık:
      - Her döngüde AKD net_lot yönü (pozitif/negatif) kaydedilir.
      - Son _LOOKBACK periyotta pozitif (alım) oranı hesaplanır.
      - Oran >= _MIN_RATIO → Kurum "kalıcı alıcı" → GEÇTİ
      - Oran <  _MIN_RATIO → Kurum "günlükçü/spekülatör" → ŞÜPHELI
    """

    def __init__(self):
        # {ticker: deque([+1 / -1 / 0, ...])} son N periyot yön geçmişi
        self._direction_history: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=_LOOKBACK)
        )
        # {ticker: {"flip_count": int, "hold_count": int}}
        self._stats: dict[str, dict] = defaultdict(
            lambda: {"flip_count": 0, "hold_count": 0}
        )

    # ----------------------------------------------------------
    # Güncelleme
    # ----------------------------------------------------------

    def update(self, ticker: str, net_lot: float):
        """
        Her döngüde net_lot yönünü geçmişe kaydeder.
        +1 → Alım  |  -1 → Satış  |  0 → Nötr
        """
        if net_lot > 0:
            direction = 1
        elif net_lot < 0:
            direction = -1
        else:
            direction = 0

        history = self._direction_history[ticker]

        # Yön değişimi tespiti (flip)
        if history and direction != 0 and history[-1] != 0:
            if history[-1] != direction:
                self._stats[ticker]["flip_count"] += 1
            else:
                self._stats[ticker]["hold_count"] += 1

        history.append(direction)

    def update_all(self, akd_metrics: dict):
        """Tüm hisseler için toplu güncelleme."""
        for ticker, metrics in akd_metrics.items():
            self.update(ticker, metrics.get("net_lot", 0))

    # ----------------------------------------------------------
    # Analiz
    # ----------------------------------------------------------

    def is_permanent_buyer(self, ticker: str) -> bool:
        """
        Son _LOOKBACK periyottaki alım oranı >= _MIN_RATIO mı?
        True → Kalıcı alıcı  |  False → Şüpheli / günlükçü
        """
        history = list(self._direction_history[ticker])
        if not history:
            return True   # Veri yoksa varsayılan olarak geçir

        buy_count   = history.count(1)
        valid_count = sum(1 for d in history if d != 0)

        if valid_count == 0:
            return True

        consistency = buy_count / valid_count
        logger.debug(
            f"[AntiFlip] {ticker} → Alım Oranı: {consistency:.2%}  "
            f"(Eşik: {_MIN_RATIO:.0%})"
        )
        return consistency >= _MIN_RATIO

    def get_flip_score(self, ticker: str) -> float:
        """
        0.0 → Sık yön değiştiriyor (spekülatör)
        1.0 → Hiç yön değiştirmemiş (kalıcı alıcı)
        """
        stats = self._stats[ticker]
        total = stats["flip_count"] + stats["hold_count"]
        if total == 0:
            return 1.0
        return round(stats["hold_count"] / total, 4)

    def get_report(self, ticker: str) -> dict:
        """Ticker için tam Anti-Flip raporu döner."""
        history     = list(self._direction_history[ticker])
        valid       = [d for d in history if d != 0]
        buy_count   = valid.count(1)
        sell_count  = valid.count(-1)
        consistency = buy_count / len(valid) if valid else 0

        return {
            "ticker":          ticker,
            "periods_analyzed": len(history),
            "buy_count":       buy_count,
            "sell_count":      sell_count,
            "consistency":     round(consistency, 4),
            "flip_score":      self.get_flip_score(ticker),
            "is_permanent":    self.is_permanent_buyer(ticker),
            "verdict":         "PERMANENT_BUYER" if self.is_permanent_buyer(ticker)
                               else "FLIPPER_WARNING",
        }
