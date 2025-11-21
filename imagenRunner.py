import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from imagen import Imagen, crop_center

# Parse args
lat = float(sys.argv[1])
lon = float(sys.argv[2])
zoom = int(sys.argv[3])
radius = int(sys.argv[4])
provider = sys.argv[5]
crop = "--crop" in sys.argv  # Check for crop flag

# Download tiles
img = Imagen(provider=provider).getMegaStitchedTiles(lat, lon, zoom, radius)

# Crop to center if requested (focus on target building)
if crop:
    img = crop_center(img, 640, 640)

output = f"tile_{lat}_{lon}_{zoom}.png"
img.save(output)

print(output)
