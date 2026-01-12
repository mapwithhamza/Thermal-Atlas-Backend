import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

print("Importing Temp...")
try:
    from backend.data_processing import calculate_temperature_sentinel
    print("Temp SUCCESS")
except Exception as e:
    print(f"Temp FAILED: {e}")

print("Importing NDVI...")
try:
    from backend.data_processing import calculate_ndvi
    print("NDVI SUCCESS")
except Exception as e:
    print(f"NDVI FAILED: {e}")
