import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import Sidebar from "./components/Sidebar";
import MapPicker from "./components/MapPicker";
import ResultsView, { AiResult, SiteMeta } from "./components/ResultsView";
import SplashScreen from "./components/SplashScreen";

type FetchParams = {
  zoom: number;
  radius: number;
  provider: string;
};

type View = "select" | "results";

export default function App() {
  const [showSplash, setShowSplash] = useState(true);
  const [lat, setLat] = useState(12.8604075);
  const [lon, setLon] = useState(77.6625644);
  const [view, setView] = useState<View>("select");
  const [loading, setLoading] = useState(false);
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [overlayImageSrc, setOverlayImageSrc] = useState<string | null>(null);
  const [siteMeta, setSiteMeta] = useState<SiteMeta | null>(null);
  const [aiResult, setAiResult] = useState<AiResult | null>(null);

  if (showSplash) {
    return <SplashScreen onComplete={() => setShowSplash(false)} />;
  }

  const handleAnalyze = async ({ zoom, radius, provider }: FetchParams) => {
    setLoading(true);
    console.log("Start AI analysis:", { lat, lon, zoom, radius, provider });

    try {
      // 1) Fetch stitched tile AND CROP IT
      const stitchedTile = await invoke<string>("fetch_and_crop_tile", {
        lat,
        lon,
        zoom,
        radius,
        provider,
      });

      console.log("Cropped tile data URL length:", stitchedTile?.length || 0);
      setImageSrc(stitchedTile);

      // 2) Build site metadata
      const meta: SiteMeta = {
        sample_id: `${Date.now()}`,
        lat,
        lon,
        zoom,
        radius,
        provider: provider.toLowerCase(),
      };
      setSiteMeta(meta);

      // 3) Run YOLO AI model
      const aiJson = await invoke<string>("run_ai_analysis", {
        imageB64: stitchedTile,
      });

      console.log("AI JSON:", aiJson);

      // Parse only the JSON line (filter out YOLO logs)
      const lastJsonString = aiJson
        .trim()
        .split('\n')
        .filter(l => l.trim().startsWith('{'))
        .pop();
      
      if (!lastJsonString) throw new Error("No JSON detected in AI output");
      const parsed: AiResult = JSON.parse(lastJsonString);

      const fullResult = {
        ...parsed,
        sample_id: meta.sample_id,
        lat: meta.lat,
        lon: meta.lon,
      };
      setAiResult(fullResult);

      // 4) Load annotated overlay image
      if (parsed.audit_overlay_path) {
        const overlayB64 = await invoke<string>("load_overlay_image", {
          imagePath: parsed.audit_overlay_path,
        });
        setOverlayImageSrc(overlayB64);

        // Save to audit overlays folder
        await invoke("save_audit_overlay", {
          imagePath: parsed.audit_overlay_path,
          sampleId: meta.sample_id,
        });
      }

      // 5) Auto-save JSON
      await invoke("save_detection_json", {
        data: {
          ...fullResult,
          zoom,
          radius,
          provider,
        },
        filename: `detection_${meta.sample_id}.json`,
      });

      // 6) Switch to results view
      setView("results");
    } catch (err) {
      console.error("Fetch / AI failed:", err);
      alert(`AI processing failed: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  if (view === "results" && siteMeta && aiResult) {
    return (
      <ResultsView
        meta={siteMeta}
        result={aiResult}
        imageSrc={imageSrc}
        overlayImageSrc={overlayImageSrc}
        onBack={() => setView("select")}
      />
    );
  }

  return (
    <div className="flex h-screen w-screen bg-slate-950 text-white overflow-hidden min-w-0 min-h-0">
      <Sidebar
        lat={lat}
        lon={lon}
        setLat={setLat}
        setLon={setLon}
        onFetch={handleAnalyze}
        loading={loading}
      />

      <div className="flex-1 flex min-w-0 min-h-0">
        <MapPicker
          lat={lat}
          lon={lon}
          onChange={(newLat, newLon) => {
            setLat(newLat);
            setLon(newLon);
          }}
        />
      </div>
    </div>
  );
}
