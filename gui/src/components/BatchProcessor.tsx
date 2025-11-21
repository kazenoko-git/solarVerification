import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import LoadingSpinner from "./LoadingSpinner";

export default function BatchProcessor() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[]>([]);

  const handleBatchProcess = async () => {
    const file = await open({
      multiple: false,
      filters: [{
        name: "CSV",
        extensions: ["csv"]
      }]
    });

    if (!file) return;

    setLoading(true);
    setResults([]);

    try {
      const batchResults = await invoke<any[]>("process_csv_batch", {
        csvPath: file,
        zoom: 18,
        radius: 1,
        provider: "esri",
      });

      setResults(batchResults);

      await invoke("save_batch_results", {
        detections: batchResults,
        batchName: "batch",
      });

      alert(`✅ Processed ${batchResults.length} locations successfully!`);
    } catch (error) {
      console.error("Batch processing failed:", error);
      alert(`❌ Batch processing failed: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="p-6 bg-slate-900 rounded-lg border border-slate-700">
        <h3 className="text-lg font-semibold mb-3">Batch Processing</h3>
        <p className="text-sm text-slate-400 mb-4">
          Process multiple locations from a CSV file. CSV format: <code className="bg-slate-800 px-2 py-1 rounded text-amber-400">sample_id,lat,lon</code>
        </p>
        
        {loading ? (
          <LoadingSpinner size="small" message="Processing batch..." />
        ) : (
          <button
            onClick={handleBatchProcess}
            className="w-full bg-amber-500 hover:bg-amber-400 text-black font-semibold py-3 px-4 rounded-lg transition-all"
          >
            📂 Select CSV File
          </button>
        )}
      </div>

      {results.length > 0 && (
        <div className="p-6 bg-slate-900 rounded-lg border border-slate-700">
          <h4 className="font-semibold mb-3">Results Summary</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Total Processed:</span>
              <span className="font-semibold">{results.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Detections:</span>
              <span className="font-semibold text-green-400">
                {results.filter(r => r.has_solar).length}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">No Solar:</span>
              <span className="font-semibold text-red-400">
                {results.filter(r => !r.has_solar).length}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
