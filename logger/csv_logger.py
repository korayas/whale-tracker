# ============================================================
#  logger/csv_logger.py
#  Dinamik CSV Kayıt Modülü:
#  Her döngüdeki tüm metrikleri, ağırlıkları ve kararları
#  zaman damgalı .csv dosyalarına arşivler.
# ============================================================

import csv
import os
import logging
from datetime import datetime
from config import LOG_DIR, LOG_FILE_PREFIX, LOG_ROTATE_DAILY

logger = logging.getLogger(__name__)

# CSV sütun başlıkları — tam kayıt formatı
FIELDNAMES = [
    # Zaman
    "timestamp",
    # Ham Metrikler
    "ticker", "price", "volume", "net_lot", "float_lots",
    "cost_basis", "float_ratio", "absorption_velocity", "cost_basis_gap",
    # Endeks
    "index_code", "index_performance", "index_correlation",
    # LOPCOW Ağırlıkları
    "w_volume", "w_net_lot", "w_float_ratio",
    "w_absorption_velocity", "w_cost_basis_gap", "w_index_performance",
    # ALPAS Çıktısı
    "alpas_score", "rank", "d_plus", "d_minus",
    # Gatekeeper Sonuçları
    "anti_flip_passed", "anti_flip_score",
    "sector_passed", "sector_risk_level", "manipulation_risk",
    "zscore_passed", "z_score",
    # Karar
    "signal",
]


class CSVLogger:
    """
    Her döngüde tüm hisse verilerini .csv dosyasına yazar.
    LOG_ROTATE_DAILY=True ise her gün yeni dosya açar.
    """

    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        self._current_file: str = ""
        self._writer = None
        self._file_handle = None

    # ----------------------------------------------------------
    # Dosya Yönetimi
    # ----------------------------------------------------------

    def _get_filepath(self) -> str:
        """Günlük rotasyon mantığıyla dosya yolunu döner."""
        if LOG_ROTATE_DAILY:
            date_str = datetime.now().strftime("%Y-%m-%d")
            return os.path.join(LOG_DIR, f"{LOG_FILE_PREFIX}_{date_str}.csv")
        return os.path.join(LOG_DIR, f"{LOG_FILE_PREFIX}.csv")

    def _ensure_open(self):
        """Dosya açık değilse veya rotasyon gerekiyorsa açar."""
        filepath = self._get_filepath()

        if filepath != self._current_file:
            self._close()
            self._current_file = filepath
            file_exists = os.path.isfile(filepath)

            self._file_handle = open(filepath, "a", newline="", encoding="utf-8")
            self._writer = csv.DictWriter(
                self._file_handle,
                fieldnames=FIELDNAMES,
                extrasaction="ignore",
            )
            # Başlık satırını sadece yeni dosyada yaz
            if not file_exists:
                self._writer.writeheader()
                logger.info(f"[CSVLogger] Yeni log dosyası: {filepath}")

    def _close(self):
        """Açık dosyayı güvenli kapatır."""
        if self._file_handle:
            self._file_handle.flush()
            self._file_handle.close()
            self._file_handle = None
            self._writer = None

    # ----------------------------------------------------------
    # Kayıt Yazma
    # ----------------------------------------------------------

    def log(self, ticker: str, raw_data: dict, akd_metrics: dict,
            sensor_metrics: dict, index_summary: dict,
            weights: dict, alpas_result: dict,
            anti_flip_report: dict, sector_result: dict,
            zscore_result: dict) -> None:
        """
        Tek bir hisse için bir döngünün tüm verilerini kaydeder.
        """
        self._ensure_open()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        raw = raw_data.get(ticker, {})
        akd = akd_metrics.get(ticker, {})
        sns = sensor_metrics.get(ticker, {})
        alp = alpas_result.get(ticker, {})
        af  = anti_flip_report
        sec = sector_result
        zsc = zscore_result

        row = {
            # Zaman
            "timestamp":              now,
            # Ham
            "ticker":                 ticker,
            "price":                  raw.get("price", 0),
            "volume":                 raw.get("volume", 0),
            "net_lot":                akd.get("net_lot", 0),
            "float_lots":             raw.get("float_lots", 0),
            "cost_basis":             akd.get("cost_basis", 0),
            "float_ratio":            sns.get("float_ratio", 0),
            "absorption_velocity":    sns.get("absorption_velocity", 0),
            "cost_basis_gap":         sns.get("cost_basis_gap", 0),
            # Endeks
            "index_code":             index_summary.get("index_code", ""),
            "index_performance":      index_summary.get("index_performance", 0),
            "index_correlation":      index_summary.get("correlation", 0),
            # LOPCOW Ağırlıkları
            "w_volume":               weights.get("volume", 0),
            "w_net_lot":              weights.get("net_lot", 0),
            "w_float_ratio":          weights.get("float_ratio", 0),
            "w_absorption_velocity":  weights.get("absorption_velocity", 0),
            "w_cost_basis_gap":       weights.get("cost_basis_gap", 0),
            "w_index_performance":    weights.get("index_performance", 0),
            # ALPAS
            "alpas_score":            alp.get("alpas_score", 0),
            "rank":                   alp.get("rank", 0),
            "d_plus":                 alp.get("d_plus", 0),
            "d_minus":                alp.get("d_minus", 0),
            # Gatekeeper
            "anti_flip_passed":       af.get("is_permanent", True),
            "anti_flip_score":        af.get("flip_score", 1.0),
            "sector_passed":          sec.get("passed", True),
            "sector_risk_level":      sec.get("risk_level", "LOW"),
            "manipulation_risk":      sec.get("manipulation_risk", False),
            "zscore_passed":          zsc.get("passed", False),
            "z_score":                zsc.get("z_score", 0),
            # Karar
            "signal":                 alp.get("is_signal", False),
        }

        self._writer.writerow(row)
        self._file_handle.flush()

    def log_all(self, tickers: list, raw_data: dict, akd_metrics: dict,
                sensor_metrics: dict, index_summaries: dict,
                weights: dict, alpas_results: dict,
                anti_flip_reports: dict, sector_results: dict,
                zscore_results: dict) -> None:
        """Tüm hisseler için log_all() çağrısı."""
        for ticker in tickers:
            try:
                self.log(
                    ticker       = ticker,
                    raw_data     = raw_data,
                    akd_metrics  = akd_metrics,
                    sensor_metrics  = sensor_metrics,
                    index_summary   = index_summaries.get(ticker, {}),
                    weights         = weights,
                    alpas_result    = alpas_results,
                    anti_flip_report= anti_flip_reports.get(ticker, {}),
                    sector_result   = sector_results.get(ticker, {}),
                    zscore_result   = zscore_results.get(ticker, {}),
                )
            except Exception as exc:
                logger.error(f"[CSVLogger] {ticker} kaydedilemedi: {exc}")

    # ----------------------------------------------------------
    # Temizlik
    # ----------------------------------------------------------

    def close(self):
        """Uygulama kapanırken dosyayı kapat."""
        self._close()
        logger.info("[CSVLogger] Log dosyası kapatıldı.")

    def get_current_logfile(self) -> str:
        """Aktif log dosyasının yolunu döner."""
        return self._current_file
