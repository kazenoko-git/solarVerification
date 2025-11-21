import { invoke } from "@tauri-apps/api/core";
import { save } from "@tauri-apps/plugin-dialog";
import { writeTextFile } from "@tauri-apps/plugin-fs";

export interface SiteMeta {
  sample_id: string;
  lat: number;
  lon: number;
  zoom: number;
  radius: number;
  provider: string;
}

export interface AiResult {
  sample_id: string;
  lat: number;
  lon: number;
  has_solar: boolean;
  confidence: number;
  panel_count_est: number;
  pv_area_sqm_est: number;
  capacity_kw_est: number;
  qc_status: string;
  qc_notes: string[];
  bbox_or_mask: any[];
  audit_overlay_path?: string;
  image_metadata?: {
    source: string;
    capture_date: string;
  };
}

interface ResultsViewProps {
  meta: SiteMeta;
  result: AiResult;
  imageSrc: string | null;
  overlayImageSrc: string | null; // NEW: for annotated image
  onBack: () => void;
}

export default function ResultsView({ 
  meta, 
  result, 
  imageSrc, 
  overlayImageSrc, 
  onBack 
}: ResultsViewProps) {
  const handleExportJSON = async () => {
    try {
      const fullData = { ...meta, ...result };
      const defaultFileName = `detection_${meta.sample_id}_export.json`;
      
      const savePath = await save({
        defaultPath: defaultFileName,
        filters: [{ name: "JSON", extensions: ["json"] }]
      });
      
      if (!savePath) return; // User cancelled
      
      await writeTextFile(savePath, JSON.stringify(fullData, null, 2));
      alert(`✅ Exported to:\n${savePath}`);
    } catch (err) {
      console.error("Export error:", err);
      alert(`❌ Export failed: ${err}`);
    }
  };
  const handleLabelForTraining = async () => {
  try {
    // Send labeled data to backend for training
    await invoke("add_to_training_data", {
      detection: result,
      qcNotes: result.qc_notes, // User can edit before saving
    });
    alert("✅ Added to training data!");
  } catch (err) {
    alert(`❌ Failed: ${err}`);
  }
};


  const statusColor = result.has_solar
    ? result.confidence > 0.7
      ? "text-green-400"
      : "text-yellow-400"
    : "text-red-400";

  const statusIcon = result.has_solar
    ? result.confidence > 0.7
      ? "✓"
      : "⚠"
    : "✗";

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-white overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 bg-slate-900 border-b border-slate-800">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm font-medium transition-colors"
          >
            ← Back
          </button>
          <h2 className="text-xl font-bold">Detection Results</h2>
        </div>

        <button
          onClick={handleExportJSON}
          className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-black rounded-lg text-sm font-semibold transition-all"
        >
          💾 Export JSON
        </button>
        <button
          onClick={handleLabelForTraining}
          className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-black rounded-lg text-sm font-semibold transition-all"
        >
          🏷️ Train
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Image Panel - NOW SHOWS ANNOTATED OUTPUT */}
          <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
            <div className="p-4 border-b border-slate-800">
              <h3 className="font-semibold text-lg">Detection Result</h3>
            </div>
            <div className="p-4">
              {overlayImageSrc ? (
                <img
                  src={overlayImageSrc}
                  alt="AI Detection Overlay"
                  className="w-full rounded-lg"
                />
              ) : imageSrc ? (
                <img
                  src={imageSrc}
                  alt="Satellite tile"
                  className="w-full rounded-lg"
                />
              ) : (
                <div className="w-full h-64 bg-slate-800 rounded-lg flex items-center justify-center">
                  <p className="text-slate-500">No image available</p>
                </div>
              )}
            </div>
          </div>

          {/* Results Panel */}
          <div className="space-y-6">
            {/* Detection Status */}
            <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
              <h3 className="font-semibold text-lg mb-4">Detection Status</h3>
              <div className={`text-5xl font-bold ${statusColor} mb-2`}>
                {statusIcon}
              </div>
              <p className="text-2xl font-semibold mb-1">
                {result.has_solar ? "Solar Panels Detected" : "No Solar Panels"}
              </p>
              <p className="text-slate-400 text-sm">
                Confidence: {(result.confidence * 100).toFixed(1)}%
              </p>
            </div>

            {/* Metrics */}
            <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
              <h3 className="font-semibold text-lg mb-4">Installation Metrics</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-slate-400 text-sm">Panel Count</p>
                  <p className="text-2xl font-bold text-amber-400">
                    {result.panel_count_est}
                  </p>
                </div>
                <div>
                  <p className="text-slate-400 text-sm">Area (m²)</p>
                  <p className="text-2xl font-bold text-amber-400">
                    {result.pv_area_sqm_est.toFixed(1)}
                  </p>
                </div>
                <div className="col-span-2">
                  <p className="text-slate-400 text-sm">Est. Capacity</p>
                  <p className="text-3xl font-bold text-amber-400">
                    {result.capacity_kw_est.toFixed(2)} kW
                  </p>
                </div>
              </div>
            </div>

            {/* Location Info */}
            <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
              <h3 className="font-semibold text-lg mb-4">Location Details</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Latitude:</span>
                  <span className="font-mono">{meta.lat.toFixed(7)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Longitude:</span>
                  <span className="font-mono">{meta.lon.toFixed(7)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Zoom Level:</span>
                  <span>{meta.zoom}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Provider:</span>
                  <span className="uppercase">{meta.provider}</span>
                </div>
                {result.image_metadata && (
                  <>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Source:</span>
                      <span>{result.image_metadata.source}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Capture Date:</span>
                      <span>{result.image_metadata.capture_date}</span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* QC Notes - AI Generated */}
            {result.qc_notes.length > 0 && (
              <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                <h3 className="font-semibold text-lg mb-3">AI Quality Analysis</h3>
                <ul className="space-y-2">
                  {result.qc_notes.map((note, i) => (
                    <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                      <span className="text-amber-400">•</span>
                      <span>{note}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
