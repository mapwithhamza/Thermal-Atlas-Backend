import logging
import json
import os
from pathlib import Path
import sys
import numpy as np
import rasterio

# FIX: Suppress PROJ/GDAL warnings and set correct library path
os.environ['PROJ_LIB'] = os.environ.get('PROJ_LIB', 'C:\\Program Files\\PostgreSQL\\16\\share\\contrib\\postgis-3.4\\proj') 

# Add backend to path (Root is d:\Skills\Urban heat island)
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.data_processing.calculate_temperature_sentinel import SentinelTemperatureProcessor
from backend.data_processing.calculate_ndvi import SentinelNDVIProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# CONFIG
DATA_SOURCE = "sentinel"
CITY = "Los Angeles"
SENTINEL_SCENE = "S2A_MSIL2A_20240715_LA" 

# ============================================
# HELPER FUNCTIONS
# ============================================

def detect_heat_islands_simple(temp_raster, transform, crs, threshold=3.0):
    """
    Detect heat islands using simple threshold method and calculate real-world centroids.
    """
    logger.info("Detecting heat islands...")
    
    from scipy import ndimage
    from pyproj import Transformer
    
    # Calculate mean temperature
    valid_mask = ~np.isnan(temp_raster) & (temp_raster > -100)
    valid_temps = temp_raster[valid_mask]
    
    if valid_temps.size == 0:
        logger.warning("No valid temperature data for heat island detection.")
        return {'total_count': 0, 'heat_islands': []}

    mean_temp = valid_temps.mean()
    
    # Identify hotspots
    hot_mask = (temp_raster > (mean_temp + threshold)) & valid_mask
    
    # Label connected regions
    labeled, num_features = ndimage.label(hot_mask)
    heat_islands = []
    
    # Initialize Coordinate Transformer
    try:
        src_crs = crs.to_string() if crs else "epsg:32611" # Default to UTM Zone 11N for LA
        transformer = Transformer.from_crs(src_crs, "epsg:4326", always_xy=True)
    except Exception as e:
        logger.error(f"Transformer initialization failed: {e}")
        transformer = None

    for label_id in range(1, num_features + 1):
        region = labeled == label_id
        region_temps = temp_raster[region]
        region_size = region.sum()
        
        # Skip small regions (noise reduction)
        if region_size < 10:
            continue
        
        intensity = float(region_temps.mean() - mean_temp)
        
        # Classify severity
        if intensity >= 6: severity = 'extreme'
        elif intensity >= 4: severity = 'high'
        elif intensity >= 2: severity = 'medium'
        else: severity = 'low'
            
        # Calculate Centroid in pixel coordinates (y=row, x=col)
        cy, cx = ndimage.center_of_mass(region)
        
        # 1. Pixel to Projected Coordinates (x, y)
        proj_x, proj_y = transform * (cx, cy)
        
        # 2. Projected to Geographic (Lon/Lat)
        if transformer:
            lon, lat = transformer.transform(proj_x, proj_y)
        else:
            lon, lat = 0.0, 0.0
        
        heat_islands.append({
            'id': f'hi_{label_id}',
            'avg_temp': round(float(region_temps.mean()), 1),
            'max_temp': round(float(region_temps.max()), 1),
            'intensity': round(intensity, 1),
            'size_pixels': int(region_size),
            'severity': severity,
            'lat': round(float(lat), 6), # Standardized 6 decimals for GIS
            'lon': round(float(lon), 6)
        })
    
    # Sort by intensity descending
    heat_islands.sort(key=lambda x: x['intensity'], reverse=True)
    
    severity_dist = {'extreme': 0, 'high': 0, 'medium': 0, 'low': 0}
    for island in heat_islands:
        severity_dist[island['severity']] += 1
    
    result = {
        'total_count': len(heat_islands),
        'mean_temperature': round(float(mean_temp), 1),
        'threshold_used': threshold,
        'severity_distribution': severity_dist,
        'heat_islands': heat_islands[:50]  # Return top 50 for performance
    }
    
    logger.info(f"  Detected {len(heat_islands)} heat islands with valid coordinates")
    return result

def analyze_vegetation_simple(ndvi_raster):
    """
    Simple vegetation analysis based on NDVI classes
    """
    logger.info("Analyzing vegetation...")
    valid_ndvi = ndvi_raster[~np.isnan(ndvi_raster) & (ndvi_raster >= -1) & (ndvi_raster <= 1)]
    
    if valid_ndvi.size == 0:
        return {'vegetation_health': 'Unknown', 'mean_ndvi': 0}

    total = len(valid_ndvi)
    bare = (valid_ndvi < 0.2).sum()
    sparse = ((valid_ndvi >= 0.2) & (valid_ndvi < 0.5)).sum()
    moderate = ((valid_ndvi >= 0.5) & (valid_ndvi < 0.7)).sum()
    dense = (valid_ndvi >= 0.7).sum()
    
    result = {
        'total_pixels': int(total),
        'vegetation_classes': {
            'bare_soil_urban': {'count': int(bare), 'percentage': round(float(bare/total*100), 2)},
            'sparse_vegetation': {'count': int(sparse), 'percentage': round(float(sparse/total*100), 2)},
            'moderate_vegetation': {'count': int(moderate), 'percentage': round(float(moderate/total*100), 2)},
            'dense_vegetation': {'count': int(dense), 'percentage': round(float(dense/total*100), 2)}
        },
        'mean_ndvi': round(float(valid_ndvi.mean()), 3),
        'vegetation_health': 'Good' if valid_ndvi.mean() > 0.4 else 'Moderate' if valid_ndvi.mean() > 0.25 else 'Poor'
    }
    
    logger.info(f"  Vegetation Health: {result['vegetation_health']}")
    return result 

def run_complete_pipeline(city_name: str, scene_id: str):
    logger.info(f"🚀 Starting Sentinel-2 Urban Heat Island Pipeline")
    
    base_dir = Path(__file__).resolve().parent.parent.parent
    raw_data_dir = base_dir / "data" / "raw" / "sentinel2" / scene_id
    processed_dir = base_dir / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    if not raw_data_dir.exists():
        logger.error(f"Data directory not found: {raw_data_dir}")
        return False
    
    try:
        # STEP 1: TEMPERATURE
        logger.info("STEP 1: Temperature Processing")
        temp_processor = SentinelTemperatureProcessor(str(raw_data_dir))
        temp_out = str(processed_dir / "temperature_la.tif")
        temp_raster, temp_profile = temp_processor.process_swir_to_temperature(temp_out)
        
        # STEP 2: NDVI
        logger.info("STEP 2: NDVI Calculation")
        ndvi_processor = SentinelNDVIProcessor(str(raw_data_dir))
        ndvi_out = str(processed_dir / "ndvi_la.tif")
        ndvi_raster, _ = ndvi_processor.calculate_ndvi(ndvi_out)
        
        # STEP 3: HEAT ISLANDS (Using captured transform/crs)
        logger.info("STEP 3: Heat Island Detection")
        transform = temp_profile['transform']
        crs = temp_profile['crs']
        
        heat_islands = detect_heat_islands_simple(temp_raster, transform, crs)
        hi_out = processed_dir / "heat_islands.json"
        with open(hi_out, 'w') as f:
            json.dump(heat_islands, f, indent=2)
            
        # STEP 4: VEGETATION
        logger.info("STEP 4: Vegetation Analysis")
        veg_analysis = analyze_vegetation_simple(ndvi_raster)
        veg_out = processed_dir / "vegetation_analysis.json"
        with open(veg_out, 'w') as f:
            json.dump(veg_analysis, f, indent=2)
        
        logger.info("✅ PIPELINE COMPLETED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        logger.error(f"❌ PIPELINE FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run_complete_pipeline(CITY, SENTINEL_SCENE)