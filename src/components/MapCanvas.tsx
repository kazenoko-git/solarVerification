type MapCanvasProps = {
  imageSrc: string | null;
};

export default function MapCanvas({ imageSrc }: MapCanvasProps) {
  return (
    <div className="flex-1 bg-slate-950 flex items-center justify-center">
      <div className="w-[512px] h-[512px] bg-slate-900 border border-slate-800 rounded-xl flex flex-col items-center justify-center overflow-hidden">
        <div className="w-full px-4 py-2 border-b border-slate-800 text-sm text-slate-300">
          Fetched tile
        </div>
        <div className="flex-1 flex items-center justify-center bg-black">
          {imageSrc ? (
            <img
              src={imageSrc}
              alt="Fetched tile"
              className="max-w-full max-h-full object-contain"
            />
          ) : (
            <span className="text-xs text-slate-500">
              No tile yet. Enter params & click Fetch.
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
