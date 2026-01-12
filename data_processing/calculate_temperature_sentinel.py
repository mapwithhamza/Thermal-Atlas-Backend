import rasterio
import numpy as np
from pathlib import Path
import json
from scipy.ndimage import gaussian_filter

class SentinelTemperatureProcessor:
    """Process Sentinel-2 SWIR bands to estimate surface temperature"""
    
    def __init__(self, sentinel_dir):
        self.sentinel_dir = Path(sentinel_dir)
    
    def process_swir_to_temperature(self, output_path):
        """
        Estimate temperature from SWIR Band 11
        FIX: Force output to GeoTIFF format (not JP2)
        """
        
        # Find SWIR band (Band 11)
        swir_files = list(self.sentinel_dir.glob('*B11*.jp2')) or \
                     list(self.sentinel_dir.glob('*B11*.tif'))
        
        if not swir_files:
            raise FileNotFoundError(f"No Band 11 (SWIR) file found in {self.sentinel_dir}")
        
        swir_file = swir_files[0]
        print(f'Processing: {swir_file.name}')
        
        with rasterio.open(swir_file) as src:
            # Read SWIR data
            swir = src.read(1).astype(float)
            
            # Get spatial reference info
            transform = src.transform
            crs = src.crs
            height, width = swir.shape
            
            # Sentinel-2 L2A reflectance conversion
            swir_reflectance = swir / 10000.0
            swir_reflectance = np.clip(swir_reflectance, 0, 0.5)
            
            # Temperature estimation
            temp_min = 25.0  
            temp_range = 25.0  
            
            valid_swir = swir_reflectance[swir_reflectance > 0]
            if valid_swir.size > 0:
                swir_min = valid_swir.min()
                swir_max = valid_swir.max()
            else:
                swir_min = 0
                swir_max = 0.5
            
            denom = swir_max - swir_min
            if denom == 0:
                denom = 1.0
            
            swir_normalized = (swir_reflectance - swir_min) / denom
            temp_celsius = temp_min + (swir_normalized * temp_range)
            
            # Apply smoothing
            temp_celsius = gaussian_filter(temp_celsius, sigma=2)
            
            # Mask invalid values
            temp_celsius = np.where(swir == 0, np.nan, temp_celsius)
        
        # Statistics
        valid_temps = temp_celsius[~np.isnan(temp_celsius)]
        
        if valid_temps.size == 0:
            raise ValueError("No valid temperature data!")
        
        stats = {
            'min': float(valid_temps.min()),
            'max': float(valid_temps.max()),
            'mean': float(valid_temps.mean()),
            'std': float(valid_temps.std()),
            'median': float(np.median(valid_temps)),
            'note': 'Estimated from SWIR Band 11 (Sentinel-2)'
        }
        
        print(f'Temperature Stats (estimated):')
        print(f'  Min: {stats["min"]:.1f}°C')
        print(f'  Max: {stats["max"]:.1f}°C')
        print(f'  Mean: {stats["mean"]:.1f}°C')
        print(f'  Std: {stats["std"]:.1f}°C')
        
        # FIX: Create NEW GeoTIFF profile (don't copy JP2 profile)
        profile = {
            'driver': 'GTiff',          # Force GeoTIFF
            'height': height,
            'width': width,
            'count': 1,
            'dtype': 'float32',         # This is OK for GTiff
            'crs': crs,
            'transform': transform,
            'nodata': -9999,
            'compress': 'lzw',
            'tiled': True,
            'blockxsize': 256,
            'blockysize': 256
        }
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save as GeoTIFF
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(temp_celsius.astype('float32'), 1)
        
        # Save statistics
        stats_path = str(output_path).replace('.tif', '_stats.json')
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f'✓ Saved: {output_path}')
        print(f'✓ Stats: {stats_path}')
        
        return temp_celsius, profile


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        sentinel_dir = sys.argv[1]
    else:
        sentinel_dir = '../../data/raw/sentinel2/S2A_MSIL2A_20240715_LA'
    
    processor = SentinelTemperatureProcessor(sentinel_dir)
    temp_data, profile = processor.process_swir_to_temperature(
        '../../data/processed/temperature_la.tif'
    )