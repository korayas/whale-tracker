# ============================================================
#  engine/alpas.py
#  ALPAS (Adaptive Linear Programming based Approach for Scoring)
#  İdeal / Anti-İdeal uzaklık analizi ile sürdürülebilir
#  alım potansiyelini 0-1 aralığında skorlar.
# ============================================================

import math
import logging
from config import ALPAS_SIGNAL_THRESHOLD

logger = logging.getLogger(__name__)


class ALPASEngine:
    """
    ALPAS Algoritması (TOPSIS tabanlı uyarlamalı sürüm):

    1. Ağırlıklı karar matrisi oluştur  →  Vᵢⱼ = wⱼ × x̃ᵢⱼ
    2. İdeal (A⁺) ve Anti-İdeal (A⁻) çözümü belirle
    3. Her hisse için d⁺ ve d⁻ uzaklıklarını hesapla
    4. Confluence (ALPAS) skoru:  Sᵢ = d⁻ᵢ / (d⁺ᵢ + d⁻ᵢ)
    5. Skora göre sırala ve eşik üzerindekileri işaretle
    """

    # ----------------------------------------------------------
    # Ana Skorlama Metodu
    # ----------------------------------------------------------

    def score(self, normalized: dict, weights: dict) -> dict:
        """
        Parametreler:
          normalized : LOPCOW'dan gelen normalize matris
                       {"THYAO": {"volume": 0.91, ...}, ...}
          weights    : LOPCOW'dan gelen ağırlıklar
                       {"volume": 0.35, ...}

        Döner:
        {
            "THYAO": {
                "alpas_score":   0.91,
                "rank":          1,
                "d_plus":        0.043,
                "d_minus":       0.412,
                "is_signal":     True,
                "weight_impact": {"volume": 0.317, ...}
            },
            ...
        }
        """
        tickers  = list(normalized.keys())
        criteria = list(weights.keys())

        if not tickers or not criteria:
            logger.warning("[ALPAS] Boş veri — skorlama atlandı.")
            return {}

        # --- Adım 1: Ağırlıklı Matris ---
        weighted = self._build_weighted_matrix(normalized, weights, tickers, criteria)

        # --- Adım 2: İdeal & Anti-İdeal ---
        ideal, anti_ideal = self._compute_ideal(weighted, tickers, criteria)

        # --- Adım 3: Uzaklıklar ---
        distances = self._compute_distances(weighted, ideal, anti_ideal, tickers, criteria)

        # --- Adım 4: ALPAS Skoru ---
        scores = {}
        for t in tickers:
            d_plus  = distances[t]["d_plus"]
            d_minus = distances[t]["d_minus"]
            denom   = d_plus + d_minus

            alpas = round(d_minus / denom, 6) if denom > 0 else 0.0

            # Ağırlık katkısı (açıklama katmanı için)
            weight_impact = {
                c: round(weights[c] * normalized[t].get(c, 0), 4)
                for c in criteria
            }

            scores[t] = {
                "alpas_score":   alpas,
                "rank":          None,          # Sıralama sonra atanır
                "d_plus":        round(d_plus,  6),
                "d_minus":       round(d_minus, 6),
                "is_signal":     alpas >= ALPAS_SIGNAL_THRESHOLD,
                "weight_impact": weight_impact,
            }

        # --- Adım 5: Sıralama ---
        ranked = sorted(tickers, key=lambda t: scores[t]["alpas_score"], reverse=True)
        for rank, ticker in enumerate(ranked, start=1):
            scores[ticker]["rank"] = rank

        logger.info(f"[ALPAS] Skorlama tamamlandı. En yüksek: "
                    f"{ranked[0]} ({scores[ranked[0]]['alpas_score']:.4f})")
        return scores

    # ----------------------------------------------------------
    # Adım 1 — Ağırlıklı Matris
    # ----------------------------------------------------------

    def _build_weighted_matrix(self, normalized: dict, weights: dict,
                                tickers: list, criteria: list) -> dict:
        """Vᵢⱼ = wⱼ × x̃ᵢⱼ"""
        weighted = {}
        for t in tickers:
            weighted[t] = {
                c: weights.get(c, 0) * normalized[t].get(c, 0)
                for c in criteria
            }
        return weighted

    # ----------------------------------------------------------
    # Adım 2 — İdeal & Anti-İdeal
    # ----------------------------------------------------------

    def _compute_ideal(self, weighted: dict, tickers: list, criteria: list):
        """
        A⁺ = Her kriter için maksimum ağırlıklı değer  (İdeal)
        A⁻ = Her kriter için minimum ağırlıklı değer   (Anti-İdeal)
        """
        ideal      = {}
        anti_ideal = {}

        for c in criteria:
            values = [weighted[t][c] for t in tickers]
            ideal[c]      = max(values)
            anti_ideal[c] = min(values)

        return ideal, anti_ideal

    # ----------------------------------------------------------
    # Adım 3 — Öklid Uzaklıkları
    # ----------------------------------------------------------

    def _compute_distances(self, weighted: dict, ideal: dict, anti_ideal: dict,
                            tickers: list, criteria: list) -> dict:
        """
        d⁺ᵢ = √ Σⱼ (Vᵢⱼ - A⁺ⱼ)²
        d⁻ᵢ = √ Σⱼ (Vᵢⱼ - A⁻ⱼ)²
        """
        distances = {}
        for t in tickers:
            d_plus  = math.sqrt(sum(
                (weighted[t][c] - ideal[c]) ** 2 for c in criteria
            ))
            d_minus = math.sqrt(sum(
                (weighted[t][c] - anti_ideal[c]) ** 2 for c in criteria
            ))
            distances[t] = {"d_plus": d_plus, "d_minus": d_minus}

        return distances

    # ----------------------------------------------------------
    # Rapor Üretici (Telegram açıklaması için)
    # ----------------------------------------------------------

    @staticmethod
    def build_explanation(ticker: str, score_data: dict, weights: dict) -> str:
        """
        Telegram mesajına eklenecek 'Neden bu hisse?' açıklamasını üretir.
        En etkili 3 kriteri büyükten küçüğe sıralar.
        """
        impact = score_data.get("weight_impact", {})
        sorted_impact = sorted(impact.items(), key=lambda x: x[1], reverse=True)

        lines = [f"📊 *{ticker}* — ALPAS Skor: `{score_data['alpas_score']:.4f}`\n"]
        lines.append("🔍 *Kriter Etki Dökümü:*")

        label_map = {
            "volume":              "📈 Hacim",
            "net_lot":             "🏛️  Kurum Alımı",
            "float_ratio":         "🎯 Tahta Hakimiyeti",
            "absorption_velocity": "⚡ Emir Hızı",
            "cost_basis_gap":      "💰 Maliyet Avantajı",
            "index_performance":   "🏦 Endeks Desteği",
        }

        total = sum(v for _, v in sorted_impact) or 1
        for crit, val in sorted_impact[:3]:
            pct = round((val / total) * 100, 1)
            label = label_map.get(crit, crit)
            lines.append(f"  {label}: `%{pct}` etkili")

        return "\n".join(lines)
