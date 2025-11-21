from imagen import Imagen, ImagenFast
# OLD
"""
lat = 13.050167209313589
lon = 80.17752056540101

img = Imagen(provider="esri")

print("Downloading single tile…")
tile = img.getTiles(lat, lon, zoom=17   )
tile.save("test_single_tile.png")
print("Saved: test_single_tile.png")

print("Downloading stitched tiles…")
stitched = img.getStitchedTiles(lat, lon, zoom=17, radius=10)
stitched.save("test_stitched.png")
print("Saved: test_stitched.png")

print("Done!")
"""
# NEW

img = ImagenFast(provider="esri", cache_dir="./cache", concurrency=24)
big = img.getMegaStitchedTiles(12.6716, 77.5946, zoom=17, radius=10, mode="memory")
big.save("big_map.png")

