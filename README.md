# 🐋 Whale Tracker — Balina Takipçisi

> **LOPCOW & ALPAS tabanlı kurumsal balina hareketi tespit botu**  
> Matriks IQ Python API ile BIST hisselerinde büyük kurum alımlarını gerçek zamanlı tespit eder.

---

## 📐 Mimari

```
API → LOPCOW → Sensörler → ALPAS → Gatekeeper → CSV Logger → Telegram
```

| Katman | Modül | Görev |
|--------|-------|-------|
| **Veri Pipeline** | `pipeline/` | Matriks IQ API, AKD, Endeks |
| **LOPCOW** | `engine/lopcow.py` | Dinamik varyans ağırlıklandırma |
| **Sensörler** | `engine/sensors.py` | Float Ratio, Velocity, Cost-Basis |
| **ALPAS** | `engine/alpas.py` | İdeal uzaklık tabanlı skorlama |
| **Gatekeeper** | `gatekeeper/` | Anti-Flip, Sektör, Z-Score filtreleri |
| **CSV Logger** | `logger/csv_logger.py` | Backtest arşivi |
| **Çıktı** | `output/` | Telegram alarm + Isı haritası |

---

## 🚀 Kurulum

```bash
# 1. Repoyu klonla
git clone https://github.com/korayas/whale-tracker.git
cd whale-tracker

# 2. (Opsiyonel) Sanal ortam oluştur
python -m venv venv
venv\Scripts\activate   # Windows

# 3. Bağımlılıkları kur
pip install -r requirements.txt

# 4. API anahtarlarını ayarla
# config.py içindeki alanları doldur:
#   MATRIKS_API_KEY   → Matriks IQ API anahtarın
#   TELEGRAM_BOT_TOKEN → Telegram bot token
#   TELEGRAM_CHAT_ID   → Telegram chat ID
```

---

## ▶️ Çalıştırma

```bash
# Mock mod (API olmadan test)
python main.py

# Gerçek Matriks IQ API ile
python main.py --live
```

---

## 🧪 Testler

```bash
# Tüm testleri çalıştır
python -m pytest tests/ -v

# Tek modül testi
python tests/test_lopcow.py
python tests/test_alpas.py
python tests/test_sensors.py
```

---

## 📊 Matematiksel Temel

### LOPCOW — Dinamik Ağırlıklandırma

$$\tilde{x}_{ij} = \frac{x_{ij} - x_j^{min}}{x_j^{max} - x_j^{min}}$$

$$w_j = \frac{Var(\ln(\tilde{x}_{ij}))}{\sum_k Var(\ln(\tilde{x}_{ik}))}$$

### ALPAS — Confluence Skoru

$$S_i = \frac{d_i^-}{d_i^+ + d_i^-} \in [0, 1]$$

### Analitik Sensörler

| Sensör | Formül |
|--------|--------|
| Float Ratio | `Net Lot / Fiili Dolaşım` |
| Velocity | `ΔLot / Δt` (lot/sn) |
| Cost Gap | `(Fiyat - Maliyet) / Fiyat` |
| Z-Score | `(Hacim - μ) / σ` |

---

## 📁 Klasör Yapısı

```
whale-tracker/
├── main.py                  # Ana döngü
├── config.py                # Ayarlar & API anahtarları
├── requirements.txt
├── .gitignore
├── pipeline/
│   ├── data_feed.py         # Matriks IQ bağlantısı
│   ├── akd_parser.py        # AKD veri işleme
│   └── index_monitor.py     # Endeks takip & korelasyon
├── engine/
│   ├── lopcow.py            # LOPCOW ağırlıklandırma
│   ├── alpas.py             # ALPAS skorlama
│   └── sensors.py           # Float Ratio, Velocity, Cost-Basis
├── gatekeeper/
│   ├── anti_flip.py         # Kurum karakter analizi
│   ├── sector_check.py      # Sektörel onay
│   └── zscore_filter.py     # Hacim Z-Score
├── logger/
│   └── csv_logger.py        # Dinamik CSV kaydı
├── output/
│   ├── telegram_bot.py      # Telegram alarm
│   └── heatmap.py           # Isı haritası (opsiyonel)
├── data/
│   └── logs/                # .csv ve .log arşivleri
└── tests/
    ├── test_lopcow.py
    ├── test_alpas.py
    └── test_sensors.py
```

---

## 📡 Telegram Sinyal Örneği

```
╔══════════════════════╗
║  🐋  BALINA TESPİTİ  ║
╚══════════════════════╝

📌 Hisse     : THYAO
🕐 Saat      : 13.05.2026 14:32:15
🏆 ALPAS Skor: 0.9200
📊 Sıralama  : #1

🔍 Kriter Etki Dökümü:
  🏛️ Kurum Alımı: %42 etkili
  📈 Hacim: %31 etkili
  ⚡ Emir Hızı: %18 etkili

🛡️ Gatekeeper Sonuçları:
  ✅ Kurum Karakteri: Kalıcı Alıcı
  📡 Sektör Riski : LOW
  📊 Z-Score      : 3.21
  🔍 Manipülasyon : 🟢 Temiz
```

---

## ⚠️ Yasal Uyarı

Bu araç yalnızca **eğitim ve araştırma** amaçlıdır. Yatırım tavsiyesi değildir.  
Her türlü finansal karar kullanıcının sorumluluğundadır.

---

## 📜 Lisans

MIT License — © 2026 korayas
