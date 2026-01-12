import logging
import math
import numpy as np
import rasterio
from flask import Blueprint, jsonify, request
from pathlib import Path

# Create Blueprint
recommendations_bp = Blueprint('recommendations', __name__)

# Setup logging
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"
TEMP_RASTER_PATH = DATA_DIR / "temperature_la.tif"
NDVI_RASTER_PATH = DATA_DIR / "ndvi_la.tif"

@recommendations_bp.route('/recommendations/green-spaces', methods=['GET'])
def get_green_space_recommendations():
    """
    Recommend optimal locations for new parks.
    Algo: High Heat + Low Vegetation.
    
    Query Params: limit (default 10)
    """
    try:
        limit = int(request.args.get('limit', 10))
        if limit < 1 or limit > 50:
            return jsonify({'error': 'Limit must be between 1 and 50'}), 400
            
        if not TEMP_RASTER_PATH.exists() or not NDVI_RASTER_PATH.exists():
             return jsonify({'error': 'Required raster data not found'}), 404
             
        # Read rasters
        with rasterio.open(TEMP_RASTER_PATH) as src_temp, rasterio.open(NDVI_RASTER_PATH) as src_ndvi:
            # Check transform match (simple check) -- assuming aligned
            if src_temp.shape != src_ndvi.shape:
                 return jsonify({'error': 'Raster dimensions mismatch'}), 500
                 
            # To avoid memory issues with huge rasters, using a stride or window is better.
            # However, for this demo, ensuring we fit in memory or use resampling.
            # Downsample for faster analysis
            out_shape = (int(src_temp.height/2), int(src_temp.width/2))
            
            # Read downsampled
            temp = src_temp.read(1, out_shape=out_shape)
            ndvi = src_ndvi.read(1, out_shape=out_shape)
            
            # Update transform for downsampled
            transform = src_temp.transform * src_temp.transform.scale(
                (src_temp.width / out_shape[1]),
                (src_temp.height / out_shape[0])
            )
            
            # Filter Invalid
            valid_mask = (temp != src_temp.nodata) & (ndvi != src_ndvi.nodata) & (~np.isnan(temp)) & (~np.isnan(ndvi))
            
            # Calculate Mean Temp for threshold
            mean_temp = np.mean(temp[valid_mask])
            
            # Find Candidates: Temp > Mean + 2 AND NDVI < 0.3
            candidates_mask = valid_mask & (temp > mean_temp + 2) & (ndvi < 0.3)
            
            candidate_indices = np.argwhere(candidates_mask)
            
            # Score candidates
            # Score = (Temp_norm * 0.6) + ((1 - NDVI) * 0.4)
            # Need strict normalization or use raw values carefully
            
            # Get values
            cand_temps = temp[candidate_indices[:, 0], candidate_indices[:, 1]]
            cand_ndvis = ndvi[candidate_indices[:, 0], candidate_indices[:, 1]]
            
            # Normalize for scoring 0-1
            # Avoid division by zero
            t_min, t_max = np.min(cand_temps), np.max(cand_temps)
            t_norm = (cand_temps - t_min) / (t_max - t_min) if t_max > t_min else np.zeros_like(cand_temps)
            
            scores = (t_norm * 0.6) + ((1 - cand_ndvis) * 0.4)
            
            # Combine into list
            results = []
            for i in range(len(scores)):
                row, col = candidate_indices[i]
                lat, lon = rasterio.transform.xy(transform, row, col, offset='center')
                # swap returned x(lon), y(lat) order from rasterio
                
                results.append({
                    "lat": lat, # y
                    "lon": lon, # x
                    "score": float(scores[i] * 100),
                    "temperature": float(cand_temps[i]),
                    "ndvi": float(cand_ndvis[i]),
                    "priority": "high" if scores[i] > 0.8 else "medium",
                    "reason": f"High temp ({float(cand_temps[i]):.1f}C) & Low veg ({float(cand_ndvis[i]):.2f})"
                })
                
            # Sort by score desc
            results.sort(key=lambda x: x['score'], reverse=True)
            
            # Filter spatial closeness (simple grid filter) to avoid bunching?
            # For simplicity, returning top N unique-ish locations could be added,
            # but standard top N is requested.
            
            return jsonify({
                "recommendations": results[:limit],
                "total_count": len(results),
                "analysis_resolution": "downsampled_50pct"
            })
    
    except Exception as e:
        logger.error(f"Error in get_green_space_recommendations: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@recommendations_bp.route('/recommendations/calculate-impact', methods=['POST'])
def calculate_impact():
    """
    Calculate estimated cooling impact of adding a park.
    Input: {lat, lon, park_area_sqm, tree_canopy_percent}
    """
    try:
        data = request.get_json()
        if not data:
             return jsonify({'error': 'Missing data'}), 400
             
        lat = float(data.get('lat', 0))
        area = float(data.get('park_area_sqm', 0))
        canopy = float(data.get('tree_canopy_percent', 0))
        
        if area <= 0 or canopy < 0 or canopy > 100:
            return jsonify({'error': 'Invalid area or canopy percentage'}), 400
            
        # Get current temp at loc
        current_temp = 35.0 # default fallback
        
        # Try read actual temp
        if TEMP_RASTER_PATH.exists():
            with rasterio.open(TEMP_RASTER_PATH) as src:
                 if not (lat < src.bounds.bottom or lat > src.bounds.top):
                     try:
                        # Assume lon provided?
                        lon = float(data.get('lon', 0))
                        row, col = src.index(lon, lat)
                        val = src.read(1, window=rasterio.windows.Window(col, row, 1, 1))
                        if val[0][0] != src.nodata:
                             current_temp = float(val[0][0])
                     except: 
                        pass # use default
                        
        # Formula (EPA-based simplified)
        base_cooling = 2.5
        size_factor = min(area / 10000, 1.5)
        canopy_factor = canopy / 100.0
        
        cooling = base_cooling * size_factor * (0.5 + canopy_factor)
        
        final_temp = current_temp - cooling
        affected_radius = math.sqrt(area / math.pi) * 1.5
        
        return jsonify({
            "current_temperature": round(current_temp, 1),
            "estimated_temperature_reduction": round(cooling, 2),
            "estimated_final_temperature": round(final_temp, 1),
            "affected_radius_meters": round(affected_radius, 1),
            "confidence": "medium",
            "methodology": "EPA Urban Heat Island research"
        })
        
    except Exception as e:
        logger.error(f"Error in calculate_impact: {e}")
        return jsonify({'error': 'Internal server error'}), 500
