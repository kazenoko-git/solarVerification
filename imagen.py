import asyncio, mercantile, httpx, aiofiles, requests
from PIL import Image
from io import BytesIO
from pathlib import Path
from typing import Optional
from tqdm.asyncio import tqdm_asyncio

class ImagenOld:
    def __init__(self, provider="esri", timeout=5):
        """
        provider: "esri", "google", "gibs"
        timeout: request timeout (seconds)
        """
        if provider == "osm":
            raise ValueError("OSM tiles cannot be used programmatically due to usage policy.")

        self.provider = provider
        self.timeout = timeout

    # TILE URL BUILDERS
    def _tileURL(self, x, y, z, key=None):
        # ESRI (best)
        if self.provider == "esri":
            return (f"https://services.arcgisonline.com/ArcGIS/rest/services/"
                    f"World_Imagery/MapServer/tile/{z}/{y}/{x}")
        # Google (requires API key)
        elif self.provider == "google":
            if key is None:
                raise ValueError("Google Maps provider requires API key.")
            return f"https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}&key={key}"
        # NASA GIBS (WMTS)
        if self.provider == "gibs":
            return self._getGIBS_WMS(x, y, z)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    # SINGLE TILE DOWNLOADER
    def downTile(self, x, y, z, key=None):
        if self.provider == "gibs":
            raise RuntimeError("GIBS does not support tile download. Use getTiles() only.")
        url = self._tileURL(x, y, z, key)
        resp = requests.get(url, timeout=self.timeout)

        if resp.status_code != 200:
            raise RuntimeError(f"Tile download failed ({resp.status_code}): {url}")

        try:
            return Image.open(BytesIO(resp.content)).convert("RGB")
        except Exception:
            print("DEBUG — first 200 chars of tile response:")
            print(resp.text[:200])
            raise

    # GET ONE TILE FOR AI
    def getTiles(self, lat, lon, zoom, key=None):
        # GIBS: use WMS, not mercantile tiles
        if self.provider == "gibs":
            return self._getGIBS_WMS(lat, lon, zoom)

        # All other providers
        tile = mercantile.tile(lon, lat, zoom)
        return self.downTile(tile.x, tile.y, zoom, key)

    # GET STITCHED TILE GRID (GUI)
    def getStitchedTiles(self, lat, lon, zoom, radius=1, key=None):
        """
        radius=1 → 3×3 grid
        radius=2 → 5×5 grid
        """
        # TLDR: GIBS must be kept at reasonable zooms
        # TLDR TLDR: GIBS does not work at all
        if self.provider == "gibs": raise ValueError("GIBS does not support stitched tiles. Use ESRI/Google for tiling.")
        center = mercantile.tile(lon, lat, zoom)
        tiles = []
        for dy in range(-radius, radius + 1):
            row = []
            for dx in range(-radius, radius + 1):
                tx = center.x + dx
                ty = center.y + dy
                row.append(self.downTile(tx, ty, zoom, key))
            tiles.append(row)
        row_imgs = [self._hstack(row) for row in tiles]
        final = self._vstack(row_imgs)
        return final

    # UTILITY — STACKING
    def _hstack(self, images):
        widths, heights = zip(*(img.size for img in images))
        total_width = sum(widths)
        max_height = max(heights)
        out = Image.new("RGB", (total_width, max_height))
        x_offset = 0
        for img in images:
            out.paste(img, (x_offset, 0))
            x_offset += img.width
        return out

    def _vstack(self, images):
        widths, heights = zip(*(img.size for img in images))
        max_width = max(widths)
        total_height = sum(heights)
        out = Image.new("RGB", (max_width, total_height))
        y_offset = 0
        for img in images:
            out.paste(img, (0, y_offset))
            y_offset += img.height
        return out

    # UTILITY - GIBS IS AS BAD AS GIBBS FREE ENERGY
    def _getGIBS_WMS(self, lat, lon, zoom):
        # scale degrees for zoom
        scale_deg = {
            2: 20,
            3: 10,
            4: 5,
            5: 2,
            6: 1,
        }.get(zoom, 5)

        # BBOX (WMS 1.3.0, EPSG:4326 = miny,minx,maxy,maxx)
        lat1 = lat - scale_deg
        lon1 = lon - scale_deg
        lat2 = lat + scale_deg
        lon2 = lon + scale_deg

        layer = "VIIRS_SNPP_CorrectedReflectance_TrueColor"

        url = (
            "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?"
            "service=WMS"
            "&request=GetMap"
            f"&layers={layer}"
            "&styles="
            "&width=1024&height=1024"
            "&format=image/jpeg"
            "&transparent=false"
            "&version=1.3.0"
            "&crs=EPSG:4326"
            f"&bbox={lat1},{lon1},{lat2},{lon2}"
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Imagen/1.0)"
        }
        resp = requests.get(url, headers=headers, timeout=self.timeout)
        # Check success
        if resp.status_code != 200:
            print("GIBS request failed. Status:", resp.status_code)
            print("Response text:", resp.text[:500])
            raise RuntimeError("GIBS WMS request failed.")
        # Ensure NASA returned an image
        if "image" not in resp.headers.get("Content-Type", ""):
            print("NOT AN IMAGE. Response:", resp.text[:500])
            raise RuntimeError("GIBS returned non-image data.")
        return Image.open(BytesIO(resp.content)).convert("RGB")

"""
Imagen (update)
- Async downloads with httpx
- Tile cache folder
- ESRI, Google, Bing, GIBS (WMS) providers
- Massive stitched tiles (async, concurrent)
- Two stitching modes: 'memory' (single big PIL image) or 'disk' (row-by-row files)
"""

# Helper: quadkey for Bing
def tile_xy_to_quadkey(x: int, y: int, z: int) -> str:
    quadkey = []
    for i in range(z, 0, -1):
        bit = 0
        mask = 1 << (i - 1)
        if (x & mask) != 0:
            bit += 1
        if (y & mask) != 0:
            bit += 2
        quadkey.append(str(bit))
    return "".join(quadkey)


class Imagen:
    def __init__(
        self,
        provider: str = "esri",
        cache_dir: str = "./tile_cache",
        timeout: int = 15,
        concurrency: int = 12,
        user_agent: str = "ImagenFast/1.0 (+https://example.org)",
    ):
        if provider.lower() == "osm":
            raise ValueError("OSM cannot be used programmatically; choose esri/google/bing/gibs.")
        self.provider = provider.lower()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.concurrency = concurrency
        self.user_agent = user_agent

        # httpx client will be created per run
        self._client: Optional[httpx.AsyncClient] = None

    # URL builders for providers
    def _esri_url(self, x, y, z):
        return f"https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

    def _google_url(self, x, y, z, key=None):
        if key is None:
            raise ValueError("Google provider requires API key parameter when building URLs.")
        return f"https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}&key={key}"

    def _bing_url(self, x, y, z, key=None):
        if key is None:
            raise ValueError("Bing provider requires a Bing Maps key argument.")
        quad = tile_xy_to_quadkey(x, y, z)
        return f"https://ecn.t3.tiles.virtualearth.net/tiles/a{quad}.jpeg?g=1&key={key}"

    # Cache helpers
    def _cache_path(self, provider: str, z: int, x: int, y: int, ext="png"):
        p = self.cache_dir / provider / str(z) / str(x)
        p.mkdir(parents=True, exist_ok=True)
        return p / f"{y}.{ext}"

    # Async single tile fetch (with cache)
    async def _fetch_tile_async(self, x: int, y: int, z: int, key: Optional[str] = None, force: bool = False) -> Image.Image:
        if self.provider == "gibs":
            raise RuntimeError("GIBS WMS should use getTiles(...) directly (WMS), not this tile fetch path.")

        cache_file = self._cache_path(self.provider, z, x, y, ext="jpg")
        if cache_file.exists() and not force:
            # load from disk
            try:
                return Image.open(cache_file).convert("RGB")
            except Exception:
                # corrupt cache: remove and redownload
                try:
                    cache_file.unlink()
                except Exception:
                    pass
        # Build URL
        if self.provider == "esri":
            url = self._esri_url(x, y, z)
        elif self.provider == "google":
            url = self._google_url(x, y, z, key=key)
        elif self.provider == "bing":
            url = self._bing_url(x, y, z, key=key)
        else:
            raise ValueError(f"Unknown provider for tile fetch: {self.provider}")

        headers = {"User-Agent": self.user_agent}
        # lazy client :p
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)

        # attempt with retries
        backoff = 0.5
        for attempt in range(4):
            try:
                resp = await self._client.get(url, headers=headers)
                if resp.status_code == 200 and "image" in (resp.headers.get("Content-Type") or ""):
                    # save to cache
                    async with aiofiles.open(cache_file, "wb") as f:
                        await f.write(resp.content)
                    return Image.open(BytesIO(resp.content)).convert("RGB")
                else:
                    # non-200 or non-image — raise to retry
                    msg = f"Bad response {resp.status_code} for {url} ({resp.headers.get('Content-Type')})"
                    if attempt == 3:
                        raise RuntimeError(msg)
                    await asyncio.sleep(backoff)
                    backoff *= 2
            except httpx.HTTPError as e:
                if attempt == 3:
                    raise RuntimeError(f"HTTP error fetching {url}: {e}") from e
                await asyncio.sleep(backoff)
                backoff *= 2

    # Public sync wrapper to get a single tile (handles GIBS)
    def getTiles(self, lat, lon, zoom, key: Optional[str] = None, force: bool = False) -> Image.Image:
        """
        Public synchronous entry:
        - For ESRI/Google/Bing: returns a single tile (PIL Image)
        - For GIBS: uses WMS bbox to return an image (PIL Image)
        """
        if self.provider == "gibs":
            # WMS path (synchronous)
            return self._getGIBS_WMS(lat, lon, zoom)
        # otherwise tile path (async run)
        return asyncio.run(self._get_tile_sync(lat, lon, zoom, key=key, force=force))

    async def _get_tile_sync(self, lat, lon, zoom, key=None, force=False):
        tile = mercantile.tile(lon, lat, zoom)
        img = await self._fetch_tile_async(tile.x, tile.y, zoom, key=key, force=force)
        return img

    # GIBS WMS (blocking) — tuff
    def _getGIBS_WMS(self, lat, lon, zoom):
        # map zoom -> bbox half-size in degrees (coarse heuristic)
        scale_deg = {2: 20, 3: 10, 4: 5, 5: 2, 6: 1}.get(zoom, 5)
        lat1 = lat - scale_deg
        lon1 = lon - scale_deg
        lat2 = lat + scale_deg
        lon2 = lon + scale_deg

        layer = "VIIRS_SNPP_CorrectedReflectance_TrueColor"
        # WMS 1.3.0 requires CRS and lat-first order for EPSG:4326 (miny,minx,maxy,maxx)
        bbox = f"{lat1},{lon1},{lat2},{lon2}"
        url = (
            "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?"
            "service=WMS&request=GetMap"
            f"&layers={layer}&styles=&width=1024&height=1024&format=image/jpeg"
            "&transparent=false&version=1.3.0"
            "&crs=EPSG:4326"
            f"&bbox={bbox}"
        )
        headers = {"User-Agent": self.user_agent}
        r = httpx.get(url, headers=headers, timeout=self.timeout)
        if r.status_code != 200 or "image" not in (r.headers.get("Content-Type") or ""):
            raise RuntimeError(f"GIBS WMS failed {r.status_code}: {r.text[:400]}")
        return Image.open(BytesIO(r.content)).convert("RGB")

    # Big daddy async stitching (fast)
    async def _stitch_async(self, lat, lon, zoom, radius, key=None, mode="memory", force=False):
        """
        mode: "memory" (fast, keep final image in memory) or "disk" (write row files to disk then stitch)
        """
        if self.provider == "gibs":
            raise RuntimeError("GIBS does not support stitched tiles. Use ESRI/Google/Bing for stitching.")

        center = mercantile.tile(lon, lat, zoom)
        coords = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                coords.append((center.x + dx, center.y + dy, zoom))

        total = len(coords)

        sem = asyncio.Semaphore(self.concurrency)
        results = {}

        async def worker(tx, ty, tz, idx):
            async with sem:
                try:
                    img = await self._fetch_tile_async(tx, ty, tz, key=key, force=force)
                    results[idx] = img
                except Exception as e:
                    # on failure, place a blank tile to keep grid shape
                    print(f"[WARN] failed tile {tx},{ty}@{tz}: {e}")
                    results[idx] = Image.new("RGB", (256, 256), (200, 200, 200))

        tasks = [worker(x, y, z, i) for i, (x, y, z) in enumerate(coords)]
        # tqdm progress for async tasks 
        for f in tqdm_asyncio.as_completed(tasks, total=total):
            await f  # just await to drive progress

        # Build rows
        side = radius * 2 + 1
        rows = []
        for r in range(side):
            row_imgs = []
            for c in range(side):
                idx = r * side + c
                row_imgs.append(results[idx])
            row_img = self._hstack(row_imgs)
            rows.append(row_img)

            if mode == "disk":
                # write row to temp file to conserve memory
                row_path = self.cache_dir / f"row_{r}.png"
                row_img.save(row_path)
                # free memory for this row_img
                rows[-1] = str(row_path)

        # finalize: either stitch rows in memory or read row files
        if mode == "memory":
            final = self._vstack(rows)
            return final
        else:
            # disk mode: open each row file (string path) and stitch vertically
            pil_rows = [Image.open(p).convert("RGB") for p in rows]
            final = self._vstack(pil_rows)
            # optionally delete row files
            for p in rows:
                try:
                    Path(p).unlink()
                except Exception:
                    pass
            return final

    def getMegaStitchedTiles(self, lat, lon, zoom, radius=5, key: Optional[str] = None, mode: str = "memory", force: bool = False) -> Image.Image:
        """
        Synchronous wrapper for big daddy stitched tiles.
        mode: 'memory' or 'disk' (disk safer for huge images)
        """
        return asyncio.run(self._stitch_async(lat, lon, zoom, radius, key=key, mode=mode, force=force))

    # Tiny dih sync helpers (stacking)
    def _hstack(self, images):
        widths, heights = zip(*(img.size for img in images))
        total_width = sum(widths)
        max_height = max(heights)
        out = Image.new("RGB", (total_width, max_height))
        x_offset = 0
        for img in images:
            out.paste(img, (x_offset, 0))
            x_offset += img.width
        return out

    def _vstack(self, images):
        widths, heights = zip(*(img.size for img in images))
        max_width = max(widths)
        total_height = sum(heights)
        out = Image.new("RGB", (max_width, total_height))
        y_offset = 0
        for img in images:
            out.paste(img, (0, y_offset))
            y_offset += img.height
        return out

    # Utilities
    def clear_cache(self):
        # remove cache dir entirely (use carefully)
        for child in self.cache_dir.glob("*"):
            if child.is_dir():
                for p in child.rglob("*"):
                    p.unlink()
                child.rmdir()

    def close(self):
        if self._client:
            try:
                asyncio.run(self._client.aclose())
            except Exception:
                pass


