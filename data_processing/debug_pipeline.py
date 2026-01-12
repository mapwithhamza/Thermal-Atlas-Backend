import logging
import json
import os
from pathlib import Path
import sys
import numpy as np
import rasterio

# FIX: Suppress PROJ/GDAL warnings
import os
os.environ['PROJ_LIB'] = os.environ.get('PROJ_LIB', 'C:\\Program Files\\PostgreSQL\\16\\share\\contrib\\postgis-3.4\\proj') 

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.data_processing.calculate_temperature_sentinel import SentinelTemperatureProcessor
from backend.data_processing.calculate_ndvi import SentinelNDVIProcessor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_SOURCE = "sentinel"
CITY = "Los Angeles"
SENTINEL_SCENE = "S2A_MSIL2A_20240715_LA" 

def detect_heat_islands_simple(temp_raster, transform, threshold=3.0):
    """
    Detect heat islands using simple threshold method and calculate centroids.
    """
    pass

def analyze_vegetation_simple(ndvi_raster):
    """
    Simple vegetation analysis
    """
    pass

def run_complete_pipeline(city_name: str, scene_id: str):
    logger.info("Minimal debug run")
    return True

if __name__ == "__main__":
    run_complete_pipeline(CITY, SENTINEL_SCENE)
