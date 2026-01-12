import logging
from typing import List, Dict
import numpy as np
import rasterio
from scipy.ndimage import label, measurements

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def classify_severity(intensity: float) -> str:
    """Classify Heat Island severity based on intensity (temp diff from mean)."""
    if intensity < 1.0:
        return 'low'
    elif intensity < 3.0:
        return 'medium'
    elif intensity < 5.0:
        return 'high'
    else:
        return 'extreme'

def detect_heat_islands(temp_raster: np.ndarray, threshold: float = 3.0, min_size: int = 10, nodata: float = -9999, transform=None) -> List[Dict]:
    """
    Detect urban heat islands and convert pixel coordinates to REAL Lat/Lon.
    
    Args:
        temp_raster: 2D temperature array.
        threshold: Degrees above mean to consider as heat island.
        min_size: Minimum size in pixels.
        nodata: NoData value to ignore.
        transform: The affine transform from the original TIF profile.
        
    Returns:
        List[Dict]: Objects with 'lat' and 'lon' for Mapbox/DeckGL.
    """
    # Filter valid data
    valid_mask = (temp_raster != nodata) & (~np.isnan(temp_raster))
    valid_data = temp_raster[valid_mask]
    
    if valid_data.size == 0:
        logger.warning("No valid temperature data for detection.")
        return []
        
    mean_temp = np.mean(valid_data)
    
    # Identify hotspots
    hotspot_mask = (temp_raster > (mean_temp + threshold)) & valid_mask
    
    # Label connected regions
    labeled_array, num_features = label(hotspot_mask)
    
    heat_islands = []
    slices = measurements.find_objects(labeled_array)
    
    for i, slice_obj in enumerate(slices):
        if slice_obj is None: continue
            
        feature_mask = (labeled_array[slice_obj] == (i + 1))
        pixel_count = np.sum(feature_mask)
        
        if pixel_count < min_size: continue
            
        region_temps = temp_raster[slice_obj][feature_mask]
        avg_t = float(np.mean(region_temps))
        intensity = avg_t - mean_temp
        
        # 1. Calculate Centroid in PIXELS
        coords = measurements.center_of_mass(feature_mask)
        pixel_row = coords[0] + slice_obj[0].start
        pixel_col = coords[1] + slice_obj[1].start
        
        # 2. TRANSFORM PIXELS TO LAT/LON
        # This is what makes the "Click to Locate" work!
        if transform:
            lon, lat = rasterio.transform.xy(transform, pixel_row, pixel_col)
        else:
            # Fallback if transform is missing (not ideal)
            lon, lat = 0.0, 0.0
        
        heat_islands.append({
            "id": f"hi_{i + 1}",
            "lat": round(float(lat), 6),       # ✅ Real Latitude
            "lon": round(float(lon), 6),       # ✅ Real Longitude
            "avg_temp": round(avg_t, 1),
            "max_temp": round(float(np.max(region_temps)), 1),
            "intensity": round(intensity, 1),
            "severity": classify_severity(intensity),
            "size_pixels": int(pixel_count)
        })
        
    heat_islands.sort(key=lambda x: x['intensity'], reverse=True)
    logger.info(f"Detected {len(heat_islands)} heat islands with coordinates.")
    return heat_islands