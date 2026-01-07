import pandas as pd

# CSV dosyasını oku (Dosyanın kodun olduğu klasörde olduğundan emin ol)
df = pd.read_csv("steam.csv")

# 1. Veri setinin boyutunu (Satır ve Sütun sayısı) yazdır
print(f"Dataset Boyutu (Satır, Sütun): {df.shape}")

# 2. Sütun isimlerini yazdır (Features)
print("\nSütun İsimleri:")
print(df.columns.tolist())

# 3. İlk 3 satıra göz at
print("\nÖrnek Veri:")
print(df.head(3))