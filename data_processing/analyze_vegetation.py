import logging
import json
from typing import Dict, List
import rasterio
import geopandas as gpd
import numpy as np
import pandas as pd
from rasterio.features import geometry_mask
from shapely.geometry import shape

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VegetationAnalyzer:
    """
    Analyze vegetation health and gaps using NDVI and Parks data.
    """
    
    def __init__(self, ndvi_path: str, parks_geojson_path: str):
        self.ndvi_path = ndvi_path
        self.parks_path = parks_geojson_path
        
    def calculate_park_coverage(self) -> Dict:
        """
        Calculate NDVI statistics for each park.
        """
        try:
            logger.info("Loading parks data...")
            parks = gpd.read_file(self.parks_path)
            
            summary = {
                "total_parks": len(parks),
                "parks_analysis": []
            }
            
            with rasterio.open(self.ndvi_path) as src:
                ndvi = src.read(1)
                transform = src.transform
                
                # Check CRs match implies re-projection if needed.
                # Assuming data pipeline aligned CRS (e.g. EPSG:4326 to match or UTM)
                # For this script we assume input is compatible.
                
                for idx, row in parks.iterrows():
                    geom = row.geometry
                    
                    # Create mask for this geometry
                    mask = geometry_mask([geom], transform=transform, invert=True, out_shape=ndvi.shape)
                    
                    park_pixels = ndvi[mask]
                    valid_pixels = park_pixels[park_pixels > -1] # Filter NoData
                    
                    if valid_pixels.size == 0:
                        continue
                        
                    mean_ndvi = float(np.mean(valid_pixels))
                    
                    summary["parks_analysis"].append({
                        "id": idx,  # or row.get('id')
                        "osm_id": row.get('osm_id', 'unknown'),
                        "mean_ndvi": mean_ndvi,
                        "health": "healthy" if mean_ndvi > 0.4 else "poor"
                    })
                    
            return summary
            
        except Exception as e:
            logger.error(f"Error analyzing parks: {e}")
            return {}

    def find_vegetation_gaps(self, threshold: float = 0.3) -> gpd.GeoDataFrame:
        """
        Identify areas with low vegetation (potential planting sites).
        This is complex on raster; we might return just statistics for now 
        or use simple thresholding if needed.
        """
        # Placeholder for full vectorization logic
        logger.info("Vegetation gap analysis not fully implemented in this lightweight script.")
        return gpd.GeoDataFrame()

if __name__ == "__main__":
    print("Vegetation Analyzer Initialized")
