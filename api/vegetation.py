import logging
import json
from pathlib import Path
import numpy as np
import rasterio
from flask import Blueprint, jsonify, request

# Create Blueprint
vegetation_bp = Blueprint('vegetation', __name__)

# Setup logging
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"
NDVI_RASTER_PATH = DATA_DIR / "ndvi_la.tif"
NDVI_STATS_PATH = DATA_DIR / "ndvi_la_stats.json"
VEGETATION_ANALYSIS_PATH = DATA_DIR / "vegetation_analysis.json"

@vegetation_bp.route('/vegetation/point', methods=['POST'])
def get_vegetation_point():
    """
    Get NDVI value at specific coordinate.
    
    Input:
        {"lat": float, "lon": float}
        
    Returns:
        {"ndvi": float, "vegetation_level": str, "health": str, ...}
    """
    try:
        data = request.get_json()
        if not data or 'lat' not in data or 'lon' not in data:
            return jsonify({'error': 'Missing lat/lon in request body'}), 400
            
        lat = float(data['lat'])
        lon = float(data['lon'])
        
        if not NDVI_RASTER_PATH.exists():
            return jsonify({'error': 'NDVI data not found'}), 404
            
        with rasterio.open(NDVI_RASTER_PATH) as src:
            if (lon < src.bounds.left or lon > src.bounds.right or 
                lat < src.bounds.bottom or lat > src.bounds.top):
                return jsonify({'error': 'Coordinates out of bounds'}), 400
                
            row, col = src.index(lon, lat)
            window = rasterio.windows.Window(col, row, 1, 1)
            val = src.read(1, window=window)
            ndvi_value = float(val[0][0])
            
            if src.nodata is not None and ndvi_value == src.nodata:
                return jsonify({'error': 'No data at this location'}), 404
                
            if np.isnan(ndvi_value):
                 return jsonify({'error': 'No data at this location (NaN)'}), 404

            # Classification
            if ndvi_value < 0.2:
                level = "bare_soil_urban"
                health = "none"
            elif ndvi_value < 0.5:
                level = "sparse_vegetation"
                health = "fair"
            elif ndvi_value < 0.7:
                level = "moderate_vegetation"
                health = "good"
            else:
                level = "dense_vegetation"
                health = "excellent"

            return jsonify({
                'ndvi': round(ndvi_value, 3),
                'vegetation_level': level,
                'health': health,
                'lat': lat,
                'lon': lon
            })
            
    except ValueError:
        return jsonify({'error': 'Invalid coordinate format'}), 400
    except Exception as e:
        logger.error(f"Error in get_vegetation_point: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@vegetation_bp.route('/vegetation/statistics', methods=['GET'])
def get_vegetation_statistics():
    """Return overall vegetation statistics."""
    try:
        if not NDVI_STATS_PATH.exists():
             return jsonify({'error': 'NDVI statistics not found'}), 404
             
        with open(NDVI_STATS_PATH, 'r') as f:
            stats = json.load(f)
            
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error in get_vegetation_statistics: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@vegetation_bp.route('/vegetation/analysis', methods=['GET'])
def get_vegetation_analysis():
    """Return full vegetation analysis."""
    try:
        if not VEGETATION_ANALYSIS_PATH.exists():
             return jsonify({'error': 'Vegetation analysis not found'}), 404
             
        with open(VEGETATION_ANALYSIS_PATH, 'r') as f:
            analysis = json.load(f)
            
        return jsonify(analysis)
    except Exception as e:
        logger.error(f"Error in get_vegetation_analysis: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@vegetation_bp.route('/vegetation/heatmap', methods=['GET'])
def get_vegetation_heatmap():
    """
    Return downsampled NDVI data for heatmap.
    """
    try:
        resolution = request.args.get('resolution', 'medium')
        resolutions = {'low': (100, 100), 'medium': (200, 200), 'high': (500, 500)}
        
        if resolution not in resolutions:
            return jsonify({'error': 'Invalid resolution'}), 400
            
        out_shape = resolutions[resolution]
        
        if not NDVI_RASTER_PATH.exists():
            return jsonify({'error': 'NDVI data not found'}), 404
            
        with rasterio.open(NDVI_RASTER_PATH) as src:
            data = src.read(1, out_shape=out_shape, resampling=rasterio.enums.Resampling.bilinear)
            
            data_float = data.astype(float)
            if src.nodata is not None:
                data_float[data == src.nodata] = np.nan
                
            data_list = np.where(np.isnan(data_float), None, data_float).tolist()
            
            bounds = {
                "west": src.bounds.left, "south": src.bounds.bottom,
                "east": src.bounds.right, "north": src.bounds.top
            }
            
            return jsonify({
                "data": data_list,
                "bounds": bounds,
                "resolution": list(out_shape),
                "unit": "NDVI"
            })
            
    except Exception as e:
        logger.error(f"Error in get_vegetation_heatmap: {e}")
        return jsonify({'error': 'Internal server error'}), 500
