# ============================================================
#  main.py — Whale Tracker Ana Döngü
#  Tüm katmanları orchestrate eder ve piyasa saatlerinde
#  sürekli çalışır.
# ============================================================

import time
import logging
import signal
import sys
from datetime import datetime

# ── Proje Modülleri ──────────────────────────────────────────
from config import (
    LOOP_INTERVAL_SECONDS, WATCHLIST,
    ALPAS_SIGNAL_THRESHOLD, OUTPUT
)
from pipeline.data_feed    import MatriksDataFeed
from pipeline.akd_parser   import AKDParser
from pipeline.index_monitor import IndexMonitor

from engine.lopcow  import LOPCOWEngine
from engine.alpas   import ALPASEngine
from engine.sensors import SensorEngine

from gatekeeper.anti_flip    import AntiFlipFilter
from gatekeeper.sector_check import SectorCheckFilter
from gatekeeper.zscore_filter import ZScoreFilter

from logger.csv_logger      import CSVLogger
from output.telegram_bot    import TelegramBot
from output.heatmap         import HeatmapGenerator

# ── Logging Ayarı ────────────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt = "%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/logs/whale_tracker.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("main")

# ── Graceful Shutdown ─────────────────────────────────────────
_running = True

def _handle_exit(sig, frame):
    global _running
    logger.info("⛔ Kapatma sinyali alındı. Döngü durduruluyor...")
    _running = False

signal.signal(signal.SIGINT,  _handle_exit)
signal.signal(signal.SIGTERM, _handle_exit)


# =============================================================
#  WHALE TRACKER
# =============================================================

def run(mock: bool = True):
    """
    Whale Tracker'ı başlatır.
    mock=True  → Matriks IQ olmadan test modu
    mock=False → Gerçek API bağlantısı
    """
    global _running

    logger.info("=" * 55)
    logger.info("  🐋  WHALE TRACKER  başlatılıyor...")
    logger.info(f"  Mod    : {'🔵 MOCK' if mock else '🟢 CANLI'}")
    logger.info(f"  Hisse  : {WATCHLIST}")
    logger.info(f"  Döngü  : {LOOP_INTERVAL_SECONDS}s")
    logger.info(f"  Eşik   : ALPAS > {ALPAS_SIGNAL_THRESHOLD}")
    logger.info("=" * 55)

    # ── Bileşen Başlatma ─────────────────────────────────────
    feed         = MatriksDataFeed(mock=mock)
    akd_parser   = AKDParser()
    index_mon    = IndexMonitor()

    lopcow       = LOPCOWEngine()
    alpas        = ALPASEngine()
    sensors      = SensorEngine()

    anti_flip    = AntiFlipFilter()
    sector_chk   = SectorCheckFilter()
    zscore_flt   = ZScoreFilter()

    csv_logger   = CSVLogger()
    telegram     = TelegramBot()
    heatmap      = HeatmapGenerator()

    # ── API Bağlantısı ────────────────────────────────────────
    if not feed.connect():
        logger.critical("API bağlantısı kurulamadı. Çıkılıyor.")
        sys.exit(1)

    # Telegram başlangıç bildirimi
    if OUTPUT.get("telegram_enabled"):
        telegram.send_test()

    loop_count = 0

    # ── ANA DÖNGÜ ────────────────────────────────────────────
    while _running:
        loop_start = time.time()
        loop_count += 1
        logger.info(f"\n{'─'*50}\n  Döngü #{loop_count}  |  {datetime.now().strftime('%H:%M:%S')}\n{'─'*50}")

        try:
            # ── KATMAN 1: Veri Çek ───────────────────────────
            raw_data = feed.fetch_all(WATCHLIST)
            if not raw_data:
                logger.warning("Veri alınamadı. Bekleniyor...")
                time.sleep(LOOP_INTERVAL_SECONDS)
                continue

            # ── KATMAN 1b: AKD + Endeks İşle ─────────────────
            akd_metrics    = akd_parser.parse_all(raw_data)
            index_mon.update_all(raw_data)
            index_summaries = {t: index_mon.get_summary(t) for t in raw_data}

            # ── KATMAN 3: Sensörler ───────────────────────────
            sensor_metrics = sensors.compute_all(raw_data, akd_metrics)

            # ── KATMAN 2: LOPCOW ─────────────────────────────
            feature_matrix = LOPCOWEngine.build_feature_matrix(
                raw_data, akd_metrics, sensor_metrics, index_summaries
            )
            lopcow_result  = lopcow.compute_weights(feature_matrix)
            weights        = lopcow_result["weights"]
            normalized     = lopcow_result["normalized"]

            # ── KATMAN 4: ALPAS ───────────────────────────────
            alpas_results  = alpas.score(normalized, weights)

            # ── KATMAN 5: Gatekeeper ─────────────────────────
            anti_flip.update_all(akd_metrics)
            zscore_flt.update_all(raw_data)

            anti_flip_reports = {t: anti_flip.get_report(t) for t in raw_data}
            sector_results    = sector_chk.check_all(raw_data, index_summaries)
            zscore_results    = zscore_flt.check_all(raw_data)

            # ── KATMAN 6: CSV Logger ──────────────────────────
            csv_logger.log_all(
                tickers          = list(raw_data.keys()),
                raw_data         = raw_data,
                akd_metrics      = akd_metrics,
                sensor_metrics   = sensor_metrics,
                index_summaries  = index_summaries,
                weights          = weights,
                alpas_results    = alpas_results,
                anti_flip_reports= anti_flip_reports,
                sector_results   = sector_results,
                zscore_results   = zscore_results,
            )

            # ── KATMAN 7: Sinyal & Bildirim ───────────────────
            signals_to_send = []
            for ticker, result in alpas_results.items():
                if not result.get("is_signal"):
                    continue

                # Gatekeeper özeti
                af   = anti_flip_reports.get(ticker, {})
                sec  = sector_results.get(ticker, {})
                zsc  = zscore_results.get(ticker, {})
                gk   = {
                    "anti_flip_passed":  af.get("is_permanent", True),
                    "sector_risk_level": sec.get("risk_level", "LOW"),
                    "manipulation_risk": sec.get("manipulation_risk", False),
                    "z_score":           zsc.get("z_score", 0),
                }

                logger.info(
                    f"🐋  SİNYAL → {ticker}  "
                    f"ALPAS={result['alpas_score']:.4f}  "
                    f"Rank=#{result['rank']}"
                )

                signals_to_send.append({
                    "ticker":             ticker,
                    "score_data":         result,
                    "weights":            weights,
                    "gatekeeper_summary": gk,
                })

            if signals_to_send:
                telegram.send_signals_batch(signals_to_send)
            else:
                logger.info(f"Sinyal yok. En yüksek skor: "
                            f"{max(alpas_results.items(), key=lambda x: x[1]['alpas_score'])[0]}"
                            f" = {max(v['alpas_score'] for v in alpas_results.values()):.4f}")

        except Exception as exc:
            logger.error(f"Döngü hatası: {exc}", exc_info=True)

        # ── Döngü Sonu: Süre Ayarı ────────────────────────────
        elapsed = time.time() - loop_start
        sleep   = max(0, LOOP_INTERVAL_SECONDS - elapsed)
        if _running:
            logger.debug(f"Döngü süresi: {elapsed:.2f}s  |  Bekleniyor: {sleep:.2f}s")
            time.sleep(sleep)

    # ── Temizlik ─────────────────────────────────────────────
    csv_logger.close()
    feed.disconnect()
    logger.info("✅ Whale Tracker düzgün kapatıldı.")


# =============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="🐋 Whale Tracker")
    parser.add_argument(
        "--live", action="store_true",
        help="Gerçek Matriks IQ API bağlantısı kullan (varsayılan: mock mod)"
    )
    args = parser.parse_args()

    run(mock=not args.live)
