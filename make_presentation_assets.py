import os
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Girdi dosyası konumu
CSV_PATHS = [
    Path("c:/Users/ahmet/Desktop/ML_FinalProject/steam.csv"),
    Path("c:/Users/ahmet/Desktop/ML_FinalProject/ML_FinalProject_Data/steam.csv"),
]

# Çıktı klasörleri
OUTPUT_DIR = Path("c:/Users/ahmet/Desktop/ML_FinalProject/presentation_assets")
FIG_DIR = OUTPUT_DIR / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

# CSV'yi bul ve oku
csv_path = None
for p in CSV_PATHS:
    if p.exists():
        csv_path = p
        break

if csv_path is None:
    raise FileNotFoundError("steam.csv bulunamadı. 'ML_FinalProject' kök veya 'ML_FinalProject_Data' klasörünü kontrol edin.")

# CSV okuma: hatalı satırlar ve karmaşık kaçış/tırnak durumları için toleranslı ayarlar
read_ok = False
read_errors = []
for opts in [
    {"encoding": "utf-8", "on_bad_lines": "skip", "engine": "python"},
    {"encoding": "utf-8", "on_bad_lines": "skip", "engine": "python", "sep": ",", "quotechar": '"'},
    {"encoding": "utf-8", "on_bad_lines": "skip", "engine": "python", "sep": ",", "escapechar": "\\"},
    {"encoding": "utf-8", "on_bad_lines": "skip"},
]:
    try:
        df = pd.read_csv(csv_path, **opts)
        read_ok = True
        break
    except Exception as e:
        read_errors.append(str(e))

if not read_ok:
    raise RuntimeError(
        "steam.csv okunamadı. Örnek hatalar: " + (" | ".join(read_errors[:2]))
    )

# Temel özet bilgileri
summary = {
    "dosya_yolu": str(csv_path),
    "satir_sayisi": int(df.shape[0]),
    "sutun_sayisi": int(df.shape[1]),
}

# Eksik değer sayıları
na_counts = df.isna().sum()

# Sütun türleri
dtypes = df.dtypes.astype(str)

# Özet Excel çıktısı
summary_xlsx = OUTPUT_DIR / "summary.xlsx"
with pd.ExcelWriter(summary_xlsx, engine="xlsxwriter") as writer:
    pd.DataFrame([summary]).to_excel(writer, sheet_name="ozet", index=False)
    pd.DataFrame({"sutun": df.columns, "tip": dtypes.values}).to_excel(writer, sheet_name="sutun_tipleri", index=False)
    na_counts.rename("eksik_deger_sayisi").reset_index().rename(columns={"index":"sutun"}).to_excel(writer, sheet_name="eksikler", index=False)
    df.head(10).to_excel(writer, sheet_name="ornek_ilk10", index=False)

# Uygun görülen grafikler: fiyat dağılımı, çıkış yılına göre oyun sayısı ve
# proje gerekliliklerine göre Success tanımına dayalı dağılım grafiği.
# Sütun adlarını esnekçe tahmin etmeye çalışalım
col_price = None
for c in df.columns:
    if str(c).lower() in ("price", "price_final", "steam_price"):
        col_price = c
        break

col_year = None
for c in df.columns:
    cl = str(c).lower()
    if cl in ("release_year", "year", "release_date"):
        col_year = c
        break

# Grafik: Fiyat dağılımı
if col_price and pd.api.types.is_numeric_dtype(df[col_price]):
    plt.figure(figsize=(8,5))
    df[col_price].dropna().clip(lower=0).plot(kind="hist", bins=50, color="#3b82f6")
    plt.title("Fiyat Dağılımı")
    plt.xlabel("Fiyat")
    plt.ylabel("Adet")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fiyat_dagilimi.png", dpi=150)
    plt.close()

# Grafik: Çıkış yılına göre oyun sayısı
if col_year:
    years_series = df[col_year].copy()
    # release_date ise yıl çıkaralım
    if pd.api.types.is_datetime64_any_dtype(years_series):
        years = years_series.dt.year
    else:
        # Metin ise yıl ayıklamayı deneyelim
        try:
            years = pd.to_datetime(years_series, errors="coerce").dt.year
        except Exception:
            years = pd.to_numeric(years_series, errors="coerce")
    counts = years.dropna().astype(int).value_counts().sort_index()
    if not counts.empty:
        plt.figure(figsize=(9,5))
        counts.plot(kind="bar", color="#10b981")
        plt.title("Yıla Göre Oyun Sayısı")
        plt.xlabel("Yıl")
        plt.ylabel("Adet")
        plt.tight_layout()
        plt.savefig(FIG_DIR / "yila_gore_oyun_sayisi.png", dpi=150)
        plt.close()

# Success görseli: owners ve avg playtime medianlarına göre label ve scatter
# Heuristik: owners sütunu için olası isimler, playtime için olası isimler
owners_candidates = [
    "owners", "estimated_owners", "owners_range", "steam_owners",
    "number_of_owners", "num_owners"
]
playtime_candidates = [
    "average_playtime", "avg_playtime", "mean_playtime", "playtime",
    "average_playtime_forever", "avg_playtime_forever"
]

col_owners = None
for c in df.columns:
    if str(c).lower() in owners_candidates:
        col_owners = c
        break

col_play = None
for c in df.columns:
    if str(c).lower() in playtime_candidates:
        col_play = c
        break

def _numeric_clean(s):
    # Sahiplik aralığı gibi metinleri sayıya çevirmeyi dener (örn. "20,000..50,000")
    if s.dtype == object:
        ser = s.astype(str).str.replace(",", "", regex=False)
        # Aralıksa üst sınırı alalım
        ser = ser.str.replace("..", "-", regex=False)
        ser = ser.str.split("-").str[-1]
        return pd.to_numeric(ser, errors="coerce")
    return pd.to_numeric(s, errors="coerce")

if col_owners and col_play:
    owners_num = _numeric_clean(df[col_owners])
    play_num = _numeric_clean(df[col_play])
    owners_med = owners_num.median(skipna=True)
    play_med = play_num.median(skipna=True)

    success = (owners_num >= owners_med) & (play_num >= play_med)
    label = success.map({True: "Successful", False: "Unsuccessful"})

    plot_df = pd.DataFrame({
        "Owners": owners_num,
        "AvgPlaytime": play_num,
        "Label": label
    }).dropna()

    if not plot_df.empty:
        plt.figure(figsize=(8,6))
        colors = plot_df["Label"].map({"Successful": "#16a34a", "Unsuccessful": "#ef4444"})
        plt.scatter(plot_df["Owners"], plot_df["AvgPlaytime"], c=colors, s=12, alpha=0.6)
        plt.axvline(owners_med, color="#334155", linestyle="--", linewidth=1)
        plt.axhline(play_med, color="#334155", linestyle="--", linewidth=1)
        plt.title("Success Tanımına Göre Dağılım (Owners vs Avg Playtime)")
        plt.xlabel("Estimated Owners")
        plt.ylabel("Average Playtime")
        plt.tight_layout()
        plt.savefig(FIG_DIR / "success_scatter.png", dpi=150)
        plt.close()

        # Başarı sınıf sayımları bar grafiği
        counts = plot_df["Label"].value_counts()
        plt.figure(figsize=(5,4))
        counts.plot(kind="bar", color=["#16a34a", "#ef4444"])
        plt.title("Sınıf Dağılımı")
        plt.ylabel("Adet")
        plt.tight_layout()
        plt.savefig(FIG_DIR / "success_class_counts.png", dpi=150)
        plt.close()

# Basit HTML raporu
html_path = OUTPUT_DIR / "report.html"
columns_list = "".join(f"<li>{c}</li>" for c in df.columns)
figs_html = []
for name in ["fiyat_dagilimi.png", "yila_gore_oyun_sayisi.png"]:
    f = FIG_DIR / name
    if f.exists():
        figs_html.append(f"<div><h3>{name.replace('_',' ').replace('.png','').title()}</h3><img src='figures/{name}' style='max-width:800px'></div>")

# Success görsellerini HTML'e ekle
for name in ["success_scatter.png", "success_class_counts.png"]:
    f = FIG_DIR / name
    if f.exists():
        figs_html.append(f"<div><h3>{name.replace('_',' ').replace('.png','').title()}</h3><img src='figures/{name}' style='max-width:800px'></div>")

html = f"""
<!doctype html>
<html lang='tr'>
<head>
  <meta charset='utf-8'>
  <title>Steam Dataset Raporu</title>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    h1 {{ margin-bottom: 4px; }}
    .meta {{ color: #555; margin-bottom: 16px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    img {{ border: 1px solid #ddd; padding: 8px; background: #fafafa; }}
  </style>
</head>
<body>
  <h1>Steam Dataset Raporu</h1>
  <div class='meta'>Dosya: {csv_path} • Satır: {summary['satir_sayisi']} • Sütun: {summary['sutun_sayisi']}</div>
  <h2>Sütunlar</h2>
  <ul>
    {columns_list}
  </ul>
  <h2>Örnek İlk 5 Satır</h2>
  {pd.concat([df.head(5).astype(str)], axis=1).to_html(index=False)}
  <h2>Görseller</h2>
  <div class='grid'>
    {''.join(figs_html) if figs_html else '<p>Grafik üretilmedi (uygun sütun bulunamadı).</p>'}
  </div>
  <p>Detaylı tablo ve metrikler için <strong>summary.xlsx</strong> dosyasına bakabilirsiniz.</p>
</body>
</html>
"""

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Rapor ve var ise görseller kaydedildi: {OUTPUT_DIR}")
print(f"- Excel özet: {summary_xlsx}")
print(f"- HTML rapor: {html_path}")
print(f"- Grafikler klasörü: {FIG_DIR}")
