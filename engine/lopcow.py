# ============================================================
#  engine/lopcow.py
#  LOPCOW (Logarithmic Percentage Change-based Objective
#  Weighting) — Dinamik, varyansa dayalı kriter ağırlıklandırma
# ============================================================

import math
import logging
from typing import Optional
from config import LOPCOW_EPSILON, CRITERIA_DIRECTION

logger = logging.getLogger(__name__)


class LOPCOWEngine:
    """
    LOPCOW Algoritması:

    1. Ham veri matrisini (hisse × kriter) alır.
    2. Min-Max normalizasyon uygular (0-1 aralığı).
    3. Her kriter için logaritmik varyans hesaplar.
    4. Varyans oranıyla objektif ağırlık (wⱼ) üretir.

    Referans: Ecer, F. & Pamucar, D. (2022).
    """

    CRITERIA = list(CRITERIA_DIRECTION.keys())

    # ----------------------------------------------------------
    # Ana Ağırlık Hesaplama
    # ----------------------------------------------------------

    def compute_weights(self, feature_matrix: dict) -> dict:
        """
        feature_matrix yapısı:
        {
            "THYAO": {"volume": 2500000, "net_lot": 450000, ...},
            "ASELS": {"volume": 900000,  "net_lot": 120000, ...},
            ...
        }

        Döner:
        {
            "weights": {"volume": 0.35, "net_lot": 0.42, ...},
            "normalized": {"THYAO": {"volume": 0.91, ...}, ...}
        }
        """
        tickers  = list(feature_matrix.keys())
        criteria = self.CRITERIA

        if not tickers:
            logger.warning("[LOPCOW] Boş feature_matrix — ağırlık hesaplanamadı.")
            return {"weights": {c: 1/len(criteria) for c in criteria}, "normalized": {}}

        # --- Adım 1: Normalize et ---
        normalized = self._min_max_normalize(feature_matrix, tickers, criteria)

        # --- Adım 2: Log varyansı hesapla ---
        log_variances = self._log_variance(normalized, tickers, criteria)

        # --- Adım 3: Ağırlık üret ---
        total_variance = sum(log_variances.values())
        if total_variance == 0:
            weights = {c: 1 / len(criteria) for c in criteria}
        else:
            weights = {
                c: round(log_variances[c] / total_variance, 6)
                for c in criteria
            }

        logger.debug(f"[LOPCOW] Ağırlıklar: {weights}")
        return {
            "weights":    weights,
            "normalized": normalized,
        }

    # ----------------------------------------------------------
    # Adım 1 — Min-Max Normalizasyon
    # ----------------------------------------------------------

    def _min_max_normalize(self, matrix: dict, tickers: list, criteria: list) -> dict:
        """
        Her kriter için Min-Max normalizasyon uygular.
        Fayda kriteri (benefit): x_norm = (x - min) / (max - min)
        Maliyet kriteri (cost):  x_norm = (max - x) / (max - min)
        """
        normalized = {t: {} for t in tickers}

        for crit in criteria:
            values = [matrix[t].get(crit, 0) for t in tickers]
            min_v  = min(values)
            max_v  = max(values)
            rng    = max_v - min_v if (max_v - min_v) != 0 else LOPCOW_EPSILON

            is_benefit = CRITERIA_DIRECTION.get(crit, True)

            for t in tickers:
                raw = matrix[t].get(crit, 0)
                if is_benefit:
                    norm = (raw - min_v) / rng
                else:
                    norm = (max_v - raw) / rng

                # Epsilon ekle → log(0) hatasını önle
                normalized[t][crit] = max(norm, LOPCOW_EPSILON)

        return normalized

    # ----------------------------------------------------------
    # Adım 2 — Logaritmik Varyans
    # ----------------------------------------------------------

    def _log_variance(self, normalized: dict, tickers: list, criteria: list) -> dict:
        """
        Her kriter sütunu için:
        1. Log(xᵢⱼ) al
        2. Varyansı hesapla
        Varyans yüksek → Kriter daha ayırt edici → Ağırlık yüksek
        """
        log_variances = {}

        for crit in criteria:
            log_values = [
                math.log(normalized[t][crit] + LOPCOW_EPSILON)
                for t in tickers
            ]
            mean = sum(log_values) / len(log_values)
            variance = sum((v - mean) ** 2 for v in log_values) / len(log_values)
            log_variances[crit] = variance

        return log_variances

    # ----------------------------------------------------------
    # Yardımcı: Feature Matrix Oluşturucu
    # ----------------------------------------------------------

    @staticmethod
    def build_feature_matrix(raw_data: dict, akd_metrics: dict,
                              sensor_metrics: dict, index_summaries: dict) -> dict:
        """
        Farklı kaynaklardan gelen metrikleri tek bir
        feature_matrix sözlüğünde birleştirir.
        """
        matrix = {}
        for ticker in raw_data:
            raw     = raw_data[ticker]
            akd     = akd_metrics.get(ticker, {})
            sensors = sensor_metrics.get(ticker, {})
            idx     = index_summaries.get(ticker, {})

            matrix[ticker] = {
                "volume":              raw.get("volume", 0),
                "net_lot":             max(akd.get("net_lot", 0), 0),   # Sadece pozitif alım
                "float_ratio":         sensors.get("float_ratio", 0),
                "absorption_velocity": sensors.get("absorption_velocity", 0),
                "cost_basis_gap":      max(sensors.get("cost_basis_gap", 0), 0),
                "index_performance":   max(idx.get("index_performance", 0), 0),
            }

        return matrix
