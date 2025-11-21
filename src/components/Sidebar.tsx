import { useState } from "react";
import LoadingSpinner from "./LoadingSpinner";
import BatchProcessor from "./BatchProcessor";

type SidebarProps = {
  lat: number;
  lon: number;
  setLat: (v: number) => void;
  setLon: (v: number) => void;
  onFetch: (params: { zoom: number; radius: number; provider: string }) => void;
  loading: boolean;
};

export default function Sidebar({
  lat,
  lon,
  setLat,
  setLon,
  onFetch,
  loading,
}: SidebarProps) {
  const [zoom, setZoom] = useState(18);
  const [radius, setRadius] = useState(1);
  const [provider, setProvider] = useState("esri");
  const [showBatch, setShowBatch] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onFetch({ zoom, radius, provider });
  };

  return (
    <div className="w-80 bg-slate-950 border-r border-slate-800 p-6 flex flex-col gap-6 overflow-y-auto">
      {/* Logo */}
      <div className="space-y-1">
        <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-amber-400 to-amber-600 bg-clip-text text-transparent">
          Helioscope
        </h1>
        <p className="text-xs text-slate-500">by Wing-It Team</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-800">
        <button
          onClick={() => setShowBatch(false)}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            !showBatch
              ? "text-amber-400 border-b-2 border-amber-400"
              : "text-slate-400 hover:text-slate-300"
          }`}
        >
          Single Analysis
        </button>
        <button
          onClick={() => setShowBatch(true)}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            showBatch
              ? "text-amber-400 border-b-2 border-amber-400"
              : "text-slate-400 hover:text-slate-300"
          }`}
        >
          Batch Processing
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <LoadingSpinner size="medium" message="Running AI detection..." />
        </div>
      )}

      {/* Single Analysis Form */}
      {!loading && !showBatch && (
        <form onSubmit={submit} className="flex flex-col gap-4 flex-1">
          <label className="text-sm text-slate-300">
            Latitude
            <input
              type="number"
              step="0.0000001"
              value={lat}
              onChange={(e) => setLat(parseFloat(e.target.value))}
              className="mt-1 w-full rounded-lg bg-slate-900 px-3 py-2 text-sm outline-none border border-slate-700 focus:border-amber-400 transition-colors"
            />
          </label>

          <label className="text-sm text-slate-300">
            Longitude
            <input
              type="number"
              step="0.0000001"
              value={lon}
              onChange={(e) => setLon(parseFloat(e.target.value))}
              className="mt-1 w-full rounded-lg bg-slate-900 px-3 py-2 text-sm outline-none border border-slate-700 focus:border-amber-400 transition-colors"
            />
          </label>

          <label className="text-sm text-slate-300">
            Zoom Level
            <input
              type="number"
              min={15}
              max={20}
              value={zoom}
              onChange={(e) => setZoom(parseInt(e.target.value || "18", 10))}
              className="mt-1 w-full rounded-lg bg-slate-900 px-3 py-2 text-sm outline-none border border-slate-700 focus:border-amber-400 transition-colors"
            />
            <span className="text-xs text-slate-500 mt-1 block">
              Higher zoom = more detail (recommended: 18-19)
            </span>
          </label>

          <label className="text-sm text-slate-300">
            Tile Radius
            <input
              type="number"
              min={0}
              max={5}
              value={radius}
              onChange={(e) => setRadius(parseInt(e.target.value || "1", 10))}
              className="mt-1 w-full rounded-lg bg-slate-900 px-3 py-2 text-sm outline-none border border-slate-700 focus:border-amber-400 transition-colors"
            />
            <span className="text-xs text-slate-500 mt-1 block">
              0 = single tile, 1 = 3×3 grid, 2 = 5×5 grid
            </span>
          </label>

          <label className="text-sm text-slate-300">
            Map Provider
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="mt-1 w-full rounded-lg bg-slate-900 px-3 py-2 text-sm outline-none border border-slate-700 focus:border-amber-400 transition-colors"
            >
              <option value="esri">ESRI (Recommended)</option>
              <option value="google">Google Maps</option>
              <option value="bing">Bing Maps</option>
            </select>
          </label>

          <div className="flex-1" />

          <button
            type="submit"
            className="mt-2 w-full rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-semibold py-3 text-sm transition-all duration-200 hover:shadow-lg hover:shadow-amber-500/30"
          >
            🚀 Start AI Analysis
          </button>
        </form>
      )}

      {/* Batch Processing */}
      {!loading && showBatch && (
        <div className="flex-1">
          <BatchProcessor />
        </div>
      )}
    </div>
  );
}
