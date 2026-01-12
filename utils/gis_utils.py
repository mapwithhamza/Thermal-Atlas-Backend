import math
from typing import Tuple, Optional
import rasterio

def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate latitude and longitude values.
    
    Args:
        lat (float): Latitude value (-90 to 90)
        lon (float): Longitude value (-180 to 180)
        
    Returns:
        bool: True if coordinates are valid, False otherwise.
    """
    try:
        lat = float(lat)
        lon = float(lon)
        return -90 <= lat <= 90 and -180 <= lon <= 180
    except (ValueError, TypeError):
        return False

def latlon_to_pixel(lat: float, lon: float, transform: rasterio.Affine) -> Tuple[int, int]:
    """
    Convert latitude/longitude to pixel coordinates (row, col) for a given transform.
    
    Args:
        lat (float): Latitude
        lon (float): Longitude
        transform (rasterio.Affine): Affine transform of the raster
        
    Returns:
        Tuple[int, int]: (row, column) indices
    """
    # Inverse transform converts geo coordinates to pixel coordinates
    # ~transform represents the inverse
    col, row = ~transform * (lon, lat)
    return int(row), int(col)

def pixel_to_latlon(row: int, col: int, transform: rasterio.Affine) -> Tuple[float, float]:
    """
    Convert pixel coordinates (row, col) to latitude/longitude.
    
    Args:
        row (int): Row index
        col (int): Column index
        transform (rasterio.Affine): Affine transform of the raster
        
    Returns:
        Tuple[float, float]: (latitude, longitude)
    """
    lon, lat = transform * (col, row)
    return lat, lon

def calculate_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Calculate Haversine distance between two points in kilometers.
    
    Args:
        coord1 (Tuple[float, float]): First point (lat, lon)
        coord2 (Tuple[float, float]): Second point (lat, lon)
        
    Returns:
        float: Distance in kilometers
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    R = 6371  # Earth radius in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c
