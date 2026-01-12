import rasterio
import numpy as np
from pathlib import Path
import json

class SentinelNDVIProcessor:
    """Calculate NDVI from Sentinel-2 data"""
    
    def __init__(self, sentinel_dir):
        self.sentinel_dir = Path(sentinel_dir)
    
    def calculate_ndvi(self, output_path):
        """
        Calculate NDVI from Sentinel-2 Red (B04) and NIR (B08)
        """
        
        # Find band files
        red_files = list(self.sentinel_dir.glob('*B04*.jp2')) or list(self.sentinel_dir.glob('*B04*.tif'))
        nir_files = list(self.sentinel_dir.glob('*B08*.jp2')) or list(self.sentinel_dir.glob('*B08*.tif'))
        
        if not red_files:
            raise FileNotFoundError(f"No Band 04 (Red) file found in {self.sentinel_dir}")
        if not nir_files:
            raise FileNotFoundError(f"No Band 08 (NIR) file found in {self.sentinel_dir}")
        
        red_file = red_files[0]
        nir_file = nir_files[0]
        
        print(f'Processing NDVI...')
        print(f'  Red: {red_file.name}')
        print(f'  NIR: {nir_file.name}')
        
        # Read Red band
        with rasterio.open(red_file) as red_src:
            red = red_src.read(1).astype(float)
            profile = red_src.profile.copy()
            height = red_src.height
            width = red_src.width
            crs = red_src.crs
            transform = red_src.transform
        
        # Read NIR band
        with rasterio.open(nir_file) as nir_src:
            nir = nir_src.read(1).astype(float)
        
        # Sentinel-2 L2A: values are 0-10000 (reflectance * 10000)
        # Convert to 0-1 scale
        red = red / 10000.0
        nir = nir / 10000.0
        
        # Calculate NDVI
        denominator = nir + red
        ndvi = np.where(
            denominator == 0,
            0,
            (nir - red) / denominator
        )
        
        # Clip to valid range
        ndvi = np.clip(ndvi, -1, 1)
        
        # Statistics
        valid_ndvi = ndvi[(ndvi > -1) & (ndvi < 1)]
        stats = {
            'min': float(valid_ndvi.min()),
            'max': float(valid_ndvi.max()),
            'mean': float(valid_ndvi.mean()),
            'vegetation_coverage': float((valid_ndvi > 0.3).sum() / valid_ndvi.size * 100)
        }
        
        print(f'NDVI Stats:')
        print(f'  Min: {stats["min"]:.3f}')
        print(f'  Max: {stats["max"]:.3f}')
        print(f'  Mean: {stats["mean"]:.3f}')
        print(f'  Vegetation Coverage (NDVI>0.3): {stats["vegetation_coverage"]:.1f}%')
        
        # Save
        # FIX: Force driver to GTiff and format to float32
        # Remove JP2 specific keys that cause driver errors
        for key in ['driver', 'interleave', 'tiled', 'blockxsize', 'blockysize', 'compress']:
            if key in profile:
                del profile[key]

        profile = {
            'driver': 'GTiff',
            'height': height,
            'width': width,
            'count': 1,
            'dtype': 'float32',
            'crs': crs,
            'transform': transform,
            'nodata': -9999,
            'compress': 'lzw'
        }
        
        # Ensure dir exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(ndvi.astype('float32'), 1)
        
        # Save stats
        stats_path = output_path.replace('.tif', '_stats.json')
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f'✓ Saved: {output_path}')
        
        return ndvi, profile


if __name__ == '__main__':
    processor = SentinelNDVIProcessor('../../data/raw/sentinel2/S2A_MSIL2A_20240715_LA')
    ndvi_data, profile = processor.calculate_ndvi(
        '../../data/processed/ndvi_la.tif'
    )