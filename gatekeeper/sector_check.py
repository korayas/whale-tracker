# ============================================================
#  gatekeeper/sector_check.py
#  Sektörel Onay Filtresi:
#  Endeks desteği almayan tekil hareketleri
#  "manipülasyon riski" olarak işaretler.
# ============================================================

import logging
from config import GATEKEEPER, SECTOR_INDEX_MAP

logger = logging.getLogger(__name__)

_MIN_CORR = GATEKEEPER["sector_check"]["min_correlation"]


class SectorCheckFilter:
    """
    Sektörel onay filtresi:
      - IndexMonitor'dan gelen korelasyon ve endeks performansını kullanır.
      - Düşük korelasyon + yüksek hisse hareketi = manipülasyon riski
      - Yüksek korelasyon = Sektörle uyumlu, güvenli hareket
    """

    # ----------------------------------------------------------
    # Tek Hisse Kontrolü
    # ----------------------------------------------------------

    def check(self, ticker: str, index_summary: dict,
              price_change_pct: float = 0.0) -> dict:
        """
        Parametreler:
          ticker           : Hisse sembolü
          index_summary    : IndexMonitor.get_summary() çıktısı
          price_change_pct : Hissenin % fiyat değişimi (anlık)

        Döner:
        {
            "passed":            bool,    # Filtre geçildi mi?
            "manipulation_risk": bool,    # Manipülasyon riski var mı?
            "risk_level":        str,     # "LOW" | "MEDIUM" | "HIGH"
            "reason":            str,     # Açıklama
            "correlation":       float,
            "index_code":        str,
            "index_performance": float,
        }
        """
        correlation    = index_summary.get("correlation", 0.0)
        index_perf     = index_summary.get("index_performance", 0.0)
        has_support    = index_summary.get("has_support", False)
        index_code     = index_summary.get("index_code", "XUTUM")

        # --- Risk Seviyesi Hesabı ---
        # Tek hisse güçlü hareket + endeks zayıf + korelasyon düşük = YÜKSEK RİSK
        price_move_significant = abs(price_change_pct) > 2.0
        index_weak             = abs(index_perf) < 0.5
        corr_low               = correlation < _MIN_CORR

        if price_move_significant and index_weak and corr_low:
            risk_level        = "HIGH"
            manipulation_risk = True
            passed            = False
            reason = (
                f"⚠️ Endeks desteği YOK! "
                f"Hisse: %{price_change_pct:+.1f} | "
                f"{index_code}: %{index_perf:+.1f} | "
                f"Korelasyon: {correlation:.2f} < {_MIN_CORR}"
            )

        elif corr_low and not price_move_significant:
            risk_level        = "MEDIUM"
            manipulation_risk = False
            passed            = True
            reason = (
                f"⚡ Düşük korelasyon ama hareket sınırlı. "
                f"{index_code}: %{index_perf:+.1f}"
            )

        else:
            risk_level        = "LOW"
            manipulation_risk = False
            passed            = True
            reason = (
                f"✅ Sektör onaylı. "
                f"{index_code}: %{index_perf:+.1f} | "
                f"Korelasyon: {correlation:.2f}"
            )

        logger.debug(f"[SectorCheck] {ticker} → Risk={risk_level} | {reason}")

        return {
            "passed":            passed,
            "manipulation_risk": manipulation_risk,
            "risk_level":        risk_level,
            "reason":            reason,
            "correlation":       correlation,
            "index_code":        index_code,
            "index_performance": index_perf,
        }

    # ----------------------------------------------------------
    # Toplu Kontrol
    # ----------------------------------------------------------

    def check_all(self, raw_data: dict, index_summaries: dict) -> dict:
        """
        Tüm hisseler için sektörel kontrol uygular.

        Döner:
        { "THYAO": {check_result}, ... }
        """
        results = {}
        for ticker in raw_data:
            price      = raw_data[ticker].get("price", 0)
            index_sum  = index_summaries.get(ticker, {})

            # Basit fiyat değişimi (önceki fiyat yoksa 0 kabul)
            price_change_pct = 0.0  # IndexMonitor ile geliştirilebilir

            results[ticker] = self.check(ticker, index_sum, price_change_pct)

        return results

    # ----------------------------------------------------------
    # Manipülasyon Uyarı Etiketi
    # ----------------------------------------------------------

    @staticmethod
    def manipulation_tag(risk_level: str) -> str:
        """Telegram mesajına eklenecek risk etiketi."""
        tags = {
            "LOW":    "🟢 Sektör Onaylı",
            "MEDIUM": "🟡 Düşük Korelasyon",
            "HIGH":   "🔴 MANİPÜLASYON RİSKİ",
        }
        return tags.get(risk_level, "⚪ Belirsiz")
