# ============================================================
#  pipeline/akd_parser.py
#  AKD (Aracı Kurum Dağılımı) ham verisini işler ve
#  analitik metriklere dönüştürür.
# ============================================================

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AKDParser:
    """
    AKD verisinden aşağıdaki metrikleri üretir:
      - net_lot        : Alıcı - Satıcı net lot farkı
      - cost_basis     : Alıcı kurumların ağırlıklı ortalama maliyeti
      - buyer_count    : Alıcı kurum sayısı
      - seller_count   : Satıcı kurum sayısı
      - dominant_side  : "buyer" | "seller" | "neutral"
      - concentration  : En büyük 3 kurumun toplam içindeki payı (0-1)
    """

    def parse(self, ticker: str, akd_raw: dict) -> dict:
        """
        Ham AKD sözlüğünü analitik metrik sözlüğüne dönüştürür.

        Beklenen akd_raw yapısı:
        {
            "net_lot":    int,
            "cost_basis": float,
            "buyer_institutions":  [str, ...],
            "seller_institutions": [str, ...],
        }
        """
        if not akd_raw:
            logger.warning(f"[AKDParser] {ticker} için AKD verisi boş.")
            return self._empty_metrics()

        net_lot       = akd_raw.get("net_lot", 0)
        cost_basis    = akd_raw.get("cost_basis", 0.0)
        buyers        = akd_raw.get("buyer_institutions", [])
        sellers       = akd_raw.get("seller_institutions", [])
        buyer_count   = len(buyers)
        seller_count  = len(sellers)
        total_count   = buyer_count + seller_count

        # --- Hakim taraf tespiti ---
        if net_lot > 0:
            dominant_side = "buyer"
        elif net_lot < 0:
            dominant_side = "seller"
        else:
            dominant_side = "neutral"

        # --- Konsantrasyon Oranı (CR3) ---
        # Gerçek API'den lot bazlı veriler gelirse hesaplanır.
        # Şimdilik kurum sayısı üzerinden basit oran kullanılır.
        if total_count > 0:
            top3 = min(3, buyer_count)
            concentration = top3 / total_count
        else:
            concentration = 0.0

        metrics = {
            "net_lot":       net_lot,
            "cost_basis":    cost_basis,
            "buyer_count":   buyer_count,
            "seller_count":  seller_count,
            "dominant_side": dominant_side,
            "concentration": round(concentration, 4),
        }

        logger.debug(f"[AKDParser] {ticker} → {metrics}")
        return metrics

    # ----------------------------------------------------------
    # Toplu Ayrıştırma
    # ----------------------------------------------------------

    def parse_all(self, raw_data: dict) -> dict:
        """
        fetch_all() çıktısını alarak tüm hisseler için
        AKD metriklerini üretir.

        Döner:
        {
            "THYAO": { ...akd_metrics... },
            ...
        }
        """
        results = {}
        for ticker, data in raw_data.items():
            akd_raw = data.get("akd", {})
            results[ticker] = self.parse(ticker, akd_raw)
        return results

    # ----------------------------------------------------------
    # Yardımcılar
    # ----------------------------------------------------------

    def _empty_metrics(self) -> dict:
        return {
            "net_lot":       0,
            "cost_basis":    0.0,
            "buyer_count":   0,
            "seller_count":  0,
            "dominant_side": "neutral",
            "concentration": 0.0,
        }

    def cost_basis_gap(self, price: float, cost_basis: float) -> float:
        """
        Fiyat ile kurum maliyeti arasındaki yüzdelik fark.
        Pozitif → Kurum karda (alım için uygun zemin).
        Negatif → Kurum zararda (satış baskısı riski).

        gap = (price - cost_basis) / price
        """
        if price == 0:
            return 0.0
        return round((price - cost_basis) / price, 4)

    def is_accumulation(self, metrics: dict, price: float) -> bool:
        """
        Basit birikim tespiti:
        - Net lot pozitif
        - Hakim taraf alıcı
        - Maliyet, fiyatın altında
        """
        return (
            metrics["net_lot"] > 0
            and metrics["dominant_side"] == "buyer"
            and metrics["cost_basis"] < price
        )
