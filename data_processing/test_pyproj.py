import sys
try:
    from pyproj import Transformer
    print("pyproj imported")
    transformer = Transformer.from_crs("epsg:32611", "epsg:4326", always_xy=True)
    res = transformer.transform(3705967, 310830) # Random coords from json
    print(f"Transform check: {res}")
except Exception as e:
    print(f"pyproj failed: {e}")
