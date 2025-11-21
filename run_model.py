import sys
import json
from datetime import datetime
from ultralytics import YOLO
from PIL import Image
import numpy as np
from inference import Model

def estimate_panel_metrics(masks, image_width, image_height, zoom_level=18):
    """
    Improved estimation of panel area and capacity based on masks.
    """
    if masks is None or len(masks.data) == 0:
        return 0.0, 0.0
    
    # Calculate meters per pixel at given zoom level
    meters_per_pixel = 152.87 / 256 / (2 ** (zoom_level - 18))
    
    total_area_sqm = 0.0
    
    for mask in masks.data:
        mask_pixels = mask.sum().item()
        pixel_area = mask_pixels * (meters_per_pixel ** 2)
        total_area_sqm += pixel_area
    
    watts_per_sqm = 206
    capacity_kw = (total_area_sqm * watts_per_sqm) / 1000
    
    return round(total_area_sqm, 2), round(capacity_kw, 2)

def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            "has_solar": False,
            "confidence": 0.0,
            "panel_count_est": 0,
            "pv_area_sqm_est": 0.0,
            "capacity_kw_est": 0.0,
            "qc_status": "error",
            "qc_notes": ["Invalid arguments"],
            "bbox_or_mask": [],
            "audit_overlay_path": "",
            "image_metadata": {"source": "unknown", "capture_date": "unknown"}
        }))
        return

    image_path = sys.argv[1]
    model_path = sys.argv[2]

    try:
        # Suppress YOLO verbose output
        model = YOLO(model_path)
        results = model.predict(image_path, conf=0.25, iou=0.45, verbose=False)
        result = results[0]

        # Basic detection
        has_solar = result.masks is not None and len(result.masks.data) > 0
        confidence = float(max(result.boxes.conf)) if has_solar else 0.0
        panel_count = len(result.masks.data) if has_solar else 0

        # QC Status
        qc_status = "verifiable" if has_solar and confidence > 0.5 else "not_verifiable"
        
        # Save audit overlay
        out_path = image_path.replace(".png", "_annotated.png")
        result.save(out_path)

        # Convert masks to polygons
        polygons = []
        if has_solar:
            for p in result.masks.xy:
                polygons.append(p.tolist())

        # Improved area & capacity estimation
        img = Image.open(image_path)
        area_sqm, capacity_kw = estimate_panel_metrics(
            result.masks, 
            img.width, 
            img.height
        )

        # **USE CUSTOM MODEL FOR QC NOTES**
        detection_data = {
            'confidence': confidence,
            'panel_count': panel_count,
            'area_sqm': area_sqm,
            'capacity_kw': capacity_kw,
            'has_solar': has_solar
        }
        model = Model()
        qc_notes = model.generate_notes(detection_data)

        # Image metadata
        capture_date = datetime.now().strftime("%Y-%m-%d")
        provider = "ESRI"
        
        output = {
            "has_solar": has_solar,
            "confidence": round(confidence, 3),
            "panel_count_est": panel_count,
            "pv_area_sqm_est": area_sqm,
            "capacity_kw_est": capacity_kw,
            "qc_status": qc_status,
            "qc_notes": qc_notes,
            "bbox_or_mask": polygons,
            "audit_overlay_path": out_path,
            "image_metadata": {
                "source": provider,
                "capture_date": capture_date
            }
        }

        print(json.dumps(output))

    except Exception as e:
        print(json.dumps({
            "has_solar": False,
            "confidence": 0.0,
            "panel_count_est": 0,
            "pv_area_sqm_est": 0.0,
            "capacity_kw_est": 0.0,
            "qc_status": "error",
            "qc_notes": [f"Processing error: {str(e)}"],
            "bbox_or_mask": [],
            "audit_overlay_path": "",
            "image_metadata": {"source": "unknown", "capture_date": "unknown"}
        }), file=sys.stderr)

if __name__ == "__main__":
    import sys
    import traceback
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

