import logging
import json
from pathlib import Path
import numpy as np
import rasterio
from flask import Blueprint, jsonify, request

# Create Blueprint
temperature_bp = Blueprint('temperature', __name__)

# Setup logging
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"
TEMP_RASTER_PATH = DATA_DIR / "temperature_la.tif"
TEMP_STATS_PATH = DATA_DIR / "temperature_la_stats.json"

@temperature_bp.route('/temperature/point', methods=['POST'])
def get_temperature_point():
    """
    Get temperature value at a specific coordinate.
    
    Input:
        JSON: {"lat": float, "lon": float}
        
    Returns:
        JSON: {"temperature": float, "lat": float, "lon": float, "unit": "celsius"}
    """
    try:
        data = request.get_json()
        if not data or 'lat' not in data or 'lon' not in data:
            return jsonify({'error': 'Missing lat/lon in request body'}), 400
            
        lat = float(data['lat'])
        lon = float(data['lon'])
        
        if not TEMP_RASTER_PATH.exists():
            return jsonify({'error': 'Temperature data not found'}), 404
            
        with rasterio.open(TEMP_RASTER_PATH) as src:
            # Check bounds
            if (lon < src.bounds.left or lon > src.bounds.right or 
                lat < src.bounds.bottom or lat > src.bounds.top):
                return jsonify({'error': 'Coordinates out of bounds'}), 400
                
            # Get pixel coordinates
            row, col = src.index(lon, lat)
            
            # Read value (Window(col, row, 1, 1))
            # Read integer/float data
            window = rasterio.windows.Window(col, row, 1, 1)
            val = src.read(1, window=window)
            
            temp_value = float(val[0][0])
            
            # Check nodata
            if src.nodata is not None and temp_value == src.nodata:
                return jsonify({'error': 'No data at this location'}), 404
                
            if np.isnan(temp_value):
                 return jsonify({'error': 'No data at this location (NaN)'}), 404

            return jsonify({
                'temperature': round(temp_value, 2),
                'lat': lat,
                'lon': lon,
                'unit': 'celsius'
            })
            
    except ValueError as e:
        return jsonify({'error': f'Invalid coordinate format: {e}'}), 400
    except Exception as e:
        logger.error(f"Error in get_temperature_point: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@temperature_bp.route('/temperature/statistics', methods=['GET'])
def get_temperature_statistics():
    """
    Return overall temperature statistics.
    
    Returns:
        JSON: {"min": float, "max": float, "mean": float, "std": float, ...}
    """
    try:
        if not TEMP_STATS_PATH.exists():
             return jsonify({'error': 'Temperature statistics not found'}), 404
             
        with open(TEMP_STATS_PATH, 'r') as f:
            stats = json.load(f)
            
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error in get_temperature_statistics: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@temperature_bp.route('/temperature/heatmap', methods=['GET'])
def get_temperature_heatmap():
    """
    Return downsampled temperature data for heatmap visualization.
    
    Query Params:
        resolution: 'low' | 'medium' | 'high' (default: 'medium')
        
    Returns:
        JSON: {
            "data": [[...], ...],
            "bounds": {...},
            "resolution": [width, height],
            "unit": "celsius"
        }
    """
    try:
        resolution = request.args.get('resolution', 'medium')
        
        # Define resolutions
        resolutions = {
            'low': (100, 100),
            'medium': (200, 200),
            'high': (500, 500)
        }
        
        if resolution not in resolutions:
            return jsonify({'error': f'Invalid resolution. Must be one of {list(resolutions.keys())}'}), 400
            
        out_shape = resolutions[resolution]
        
        if not TEMP_RASTER_PATH.exists():
            return jsonify({'error': 'Temperature data not found'}), 404
            
        with rasterio.open(TEMP_RASTER_PATH) as src:
            # Read and resample
            data = src.read(
                1,
                out_shape=out_shape,
                resampling=rasterio.enums.Resampling.bilinear
            )
            
            # bounds
            bounds = {
                "west": src.bounds.left,
                "south": src.bounds.bottom,
                "east": src.bounds.right,
                "north": src.bounds.top
            }
            
            # Handle NoData/NaN
            # Convert to list with None for nulls
            data_float = data.astype(float)
            if src.nodata is not None:
                data_float[data == src.nodata] = np.nan
                
            # Convert NaN to None for JSON
            # numpy array to list, replacing nan with None requires logic
            # Easiest way: where(isnan, None, val) but numpy doesn't hold None well in float array
            # Iterate or pandas conversion
            
            # Optimized approach:
            data_list = np.where(np.isnan(data_float), None, data_float).tolist()
            
            return jsonify({
                "data": data_list,
                "bounds": bounds,
                "resolution": list(out_shape),
                "unit": "celsius"
            })
            
    except Exception as e:
        logger.error(f"Error in get_temperature_heatmap: {e}")
        return jsonify({'error': 'Internal server error'}), 500
