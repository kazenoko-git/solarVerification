import { useEffect, useRef } from "react";

type MapPickerProps = {
  lat: number;
  lon: number;
  onChange: (lat: number, lon: number) => void;
};

declare global {
  interface Window {
    google?: any;
    ResizeObserver?: any;
  }
}

const GOOGLE_MAPS_API_KEY = ""; // <- replace

export default function MapPicker({ lat, lon, onChange }: MapPickerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const markerRef = useRef<any>(null);

  // Init Google Maps once
  useEffect(() => {
    const initMap = () => {
      if (!containerRef.current) return;
      if (!window.google || !window.google.maps) return;
      if (mapRef.current) return; // already initialized

      const center = { lat, lng: lon };

      const map = new window.google.maps.Map(containerRef.current, {
        center,
        zoom: 18,
        mapTypeId: "satellite",
        disableDefaultUI: false,
      });

      const marker = new window.google.maps.Marker({
        position: center,
        map,
      });

      map.addListener("click", (e: any) => {
        const clickedLat = e.latLng.lat();
        const clickedLng = e.latLng.lng();
        marker.setPosition({ lat: clickedLat, lng: clickedLng });
        onChange(clickedLat, clickedLng);
      });

      mapRef.current = map;
      markerRef.current = marker;

      // First-size fix
      setTimeout(() => {
        const g = window.google;
        if (g && g.maps) {
          g.maps.event.trigger(map, "resize");
          map.setCenter(center);
        }
      }, 50);
    };

    // Script already loaded?
    if (window.google && window.google.maps) {
      initMap();
      return;
    }

    const existing = document.getElementById(
      "gmaps-script"
    ) as HTMLScriptElement | null;

    if (existing) {
      existing.addEventListener("load", initMap, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.id = "gmaps-script";
    script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}`;
    script.async = true;
    script.defer = true;
    script.onload = initMap;
    document.head.appendChild(script);
  }, [lon, lat, onChange]);

  // Keep marker + center synced when lat/lon change externally (e.g. typing in sidebar)
  useEffect(() => {
    if (!mapRef.current || !markerRef.current) return;
    const pos = { lat, lng: lon };
    markerRef.current.setPosition(pos);
    mapRef.current.setCenter(pos);
  }, [lat, lon]);

  // ResizeObserver to keep map width responsive
  useEffect(() => {
    if (!window.ResizeObserver) return;
    if (!containerRef.current || !mapRef.current) return;

    const map = mapRef.current;
    const container = containerRef.current;
    const g = window.google;

    const observer = new window.ResizeObserver(() => {
      if (!g || !g.maps) return;
      const center = map.getCenter();
      g.maps.event.trigger(map, "resize");
      if (center) map.setCenter(center);
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  return (
  <div className="flex-1 min-w-0 min-h-0 flex flex-col bg-slate-950">
    <div className="px-4 py-2 text-xs text-slate-400 border-b border-slate-800">
      Click on the map to pick coordinates
    </div>

    <div className="flex-1 min-w-0 min-h-0">
      <div
        ref={containerRef}
        className="w-full h-full min-w-0 min-h-0"
      />
    </div>
  </div>
);

}
