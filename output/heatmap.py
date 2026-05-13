# ============================================================
#  output/heatmap.py
#  Isı Haritası Görselleştirme (Opsiyonel):
#  CSV log verilerini okuyarak hisse × zaman ısı haritası
#  oluşturur. matplotlib gerektirir.
# ============================================================

import os
import csv
import logging
from datetime import datetime
from collections import defaultdict
from config import LOG_DIR, LOG_FILE_PREFIX, OUTPUT

logger = logging.getLogger(__name__)


class HeatmapGenerator:
    """
    CSV log dosyalarından ALPAS skorlarını okuyarak
    hisse × zaman ısı haritası (heatmap) üretir.

    Gereksinim: pip install matplotlib
    """

    def __init__(self):
        self.enabled = OUTPUT.get("heatmap_enabled", False)

    # ----------------------------------------------------------
    # CSV Okuma
    # ----------------------------------------------------------

    def load_scores(self, date_str: str = None) -> dict:
        """
        Belirtilen tarihe ait CSV log dosyasını okur.
        date_str = "2026-05-13" formatında. None ise bugünü alır.

        Döner:
        {
            "THYAO": [(timestamp, alpas_score), ...],
            ...
        }
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        filepath = os.path.join(LOG_DIR, f"{LOG_FILE_PREFIX}_{date_str}.csv")

        if not os.path.isfile(filepath):
            logger.warning(f"[Heatmap] Log dosyası bulunamadı: {filepath}")
            return {}

        scores = defaultdict(list)
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get("ticker", "")
                ts     = row.get("timestamp", "")
                score  = float(row.get("alpas_score", 0))
                if ticker:
                    scores[ticker].append((ts, score))

        logger.info(f"[Heatmap] {len(scores)} hisse, {filepath} dosyasından yüklendi.")
        return dict(scores)

    # ----------------------------------------------------------
    # Görsel Üretici
    # ----------------------------------------------------------

    def generate(self, date_str: str = None, output_path: str = None) -> str:
        """
        Isı haritası PNG dosyası üretir.
        output_path belirtilmezse data/logs/ altına kaydeder.
        """
        if not self.enabled:
            logger.info("[Heatmap] Devre dışı (config.py OUTPUT['heatmap_enabled'] = False)")
            return ""

        try:
            import matplotlib.pyplot as plt
            import matplotlib.colors as mcolors
        except ImportError:
            logger.error("[Heatmap] matplotlib yüklü değil. `pip install matplotlib`")
            return ""

        scores = self.load_scores(date_str)
        if not scores:
            return ""

        tickers    = sorted(scores.keys())
        all_times  = sorted({ts for data in scores.values() for ts, _ in data})

        # Matris oluştur (NaN = veri yok)
        matrix = []
        for ticker in tickers:
            ts_map = {ts: s for ts, s in scores[ticker]}
            row    = [ts_map.get(t, None) for t in all_times]
            matrix.append(row)

        # --- Grafik ---
        fig, ax = plt.subplots(
            figsize=(max(12, len(all_times) * 0.4), max(6, len(tickers) * 0.5))
        )

        import numpy as np
        data_array = np.array(
            [[v if v is not None else float("nan") for v in row] for row in matrix],
            dtype=float,
        )

        cmap = plt.cm.RdYlGn   # Kırmızı → Sarı → Yeşil
        im   = ax.imshow(data_array, cmap=cmap, vmin=0, vmax=1, aspect="auto")

        ax.set_yticks(range(len(tickers)))
        ax.set_yticklabels(tickers, fontsize=8)
        ax.set_xticks(range(0, len(all_times), max(1, len(all_times) // 10)))
        ax.set_xticklabels(
            [all_times[i] for i in range(0, len(all_times), max(1, len(all_times) // 10))],
            rotation=45, ha="right", fontsize=7
        )

        plt.colorbar(im, ax=ax, label="ALPAS Skoru (0-1)")
        ax.set_title(
            f"🐋 Whale Tracker — ALPAS Isı Haritası  [{date_str or 'Bugün'}]",
            fontsize=13, pad=12
        )
        plt.tight_layout()

        # Kaydet
        if output_path is None:
            ds       = date_str or datetime.now().strftime("%Y-%m-%d")
            output_path = os.path.join(LOG_DIR, f"heatmap_{ds}.png")

        plt.savefig(output_path, dpi=150)
        plt.close()
        logger.info(f"[Heatmap] Kaydedildi: {output_path}")
        return output_path

    # ----------------------------------------------------------
    # Günlük Özet Raporu
    # ----------------------------------------------------------

    def daily_summary(self, date_str: str = None) -> dict:
        """
        Günlük en yüksek ALPAS skorlu hisselerin özetini döner.
        { "THYAO": {"max_score": 0.92, "signal_count": 3}, ... }
        """
        scores  = self.load_scores(date_str)
        summary = {}
        for ticker, data in scores.items():
            vals         = [s for _, s in data]
            signal_count = sum(1 for s in vals if s >= 0.85)
            summary[ticker] = {
                "max_score":    round(max(vals), 4) if vals else 0,
                "avg_score":    round(sum(vals) / len(vals), 4) if vals else 0,
                "signal_count": signal_count,
            }
        return summary
