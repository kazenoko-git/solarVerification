#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{env, fs, path::PathBuf, process::Command};
use tauri::{command, Manager};
use base64::{engine::general_purpose, Engine as _};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};


// ============================================================
// DATA STRUCTURES
// ============================================================

#[derive(Debug, Serialize, Deserialize)]
struct SolarDetection {
    sample_id: String,
    lat: f64,
    lon: f64,
    has_solar: bool,
    confidence: f64,
    panel_count_est: usize,
    pv_area_sqm_est: f64,
    capacity_kw_est: f64,
    qc_status: String,
    qc_notes: Vec<String>,
    bbox_or_mask: Vec<Vec<Vec<f64>>>,
    zoom: u32,
    radius: u32,
    provider: String,
    audit_overlay_path: Option<String>,
    image_metadata: Option<ImageMetadata>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ImageMetadata {
    source: String,
    capture_date: String,
}

#[derive(Debug, Deserialize)]
struct CsvRow {
    sample_id: String,
    lat: f64,
    lon: f64,
}

// ============================================================
// HELPER FUNCTIONS
// ============================================================

fn get_paths() -> Result<(PathBuf, PathBuf, PathBuf), String> {
    let current_dir = env::current_dir().map_err(|e| e.to_string())?;
    let gui_dir = current_dir
        .parent()
        .ok_or("Cannot find gui dir")?
        .to_path_buf();
    let project_root = gui_dir
        .parent()
        .ok_or("Cannot find project root")?
        .to_path_buf();
    
    Ok((current_dir, gui_dir, project_root))
}

// ============================================================
// TAURI COMMANDS
// ============================================================

#[command]
fn fetch_and_crop_tile(
    lat: f64,
    lon: f64,
    zoom: u32,
    radius: u32,
    provider: String,
) -> Result<String, String> {
    // Example implementation: call python with --crop flag
    let (_, gui_dir, project_root) = get_paths()?;

    let python_path = project_root.join(".venv").join("bin").join("python");
    let script_path = gui_dir.join("imagenRunner.py");

    let output = Command::new(&python_path)
        .current_dir(&gui_dir)
        .arg(&script_path)
        .arg(lat.to_string())
        .arg(lon.to_string())
        .arg(zoom.to_string())
        .arg(radius.to_string())
        .arg(&provider)
        .arg("--crop")  // Pass crop flag
        .output()
        .map_err(|e| format!("Failed to spawn python: {e}"))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python failed: {stderr}"));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let rel_path = stdout.lines().last().unwrap_or("").trim().to_string();

    if rel_path.is_empty() {
        return Err("Python did not return an output path".into());
    }

    let img_path: PathBuf = gui_dir.join(&rel_path);

    if !img_path.exists() {
        return Err(format!("Image file not found at {}", img_path.display()));
    }

    let bytes = fs::read(&img_path).map_err(|e| format!("Failed to read PNG: {e}"))?;
    let b64 = base64::engine::general_purpose::STANDARD.encode(bytes);

    Ok(format!("data:image/png;base64,{}", b64))
}


#[command]
fn fetch_stitched_tile(
    lat: f64,
    lon: f64,
    zoom: u32,
    radius: u32,
    provider: String,
) -> Result<String, String> {
    let (_, gui_dir, project_root) = get_paths()?;

    let python_path = project_root.join(".venv").join("bin").join("python");
    if !python_path.exists() {
        return Err(format!(
            "Python venv not found at {}",
            python_path.display()
        ));
    }

    let script_path = gui_dir.join("imagenRunner.py");
    if !script_path.exists() {
        return Err(format!(
            "imagenRunner.py not found at {}",
            script_path.display()
        ));
    }

    println!("Using python: {}", python_path.display());
    println!("Using script: {}", script_path.display());

    let output = Command::new(&python_path)
        .current_dir(&gui_dir)
        .arg(&script_path)
        .arg(lat.to_string())
        .arg(lon.to_string())
        .arg(zoom.to_string())
        .arg(radius.to_string())
        .arg(&provider)
        .arg("--crop")  // ADD CROP FLAG
        .output()
        .map_err(|e| format!("Failed to spawn python: {e}"))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python failed: {stderr}"));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let rel_path = stdout.lines().last().unwrap_or("").trim().to_string();

    if rel_path.is_empty() {
        return Err("Python did not return an output path".into());
    }

    let img_path: PathBuf = gui_dir.join(&rel_path);
    println!("Python output path: {}", img_path.display());

    if !img_path.exists() {
        return Err(format!("Image file not found at {}", img_path.display()));
    }

    let bytes = fs::read(&img_path).map_err(|e| format!("Failed to read PNG: {e}"))?;
    let b64 = general_purpose::STANDARD.encode(bytes);

    Ok(format!("data:image/png;base64,{}", b64))
}

#[command]
fn run_ai_analysis(image_b64: String) -> Result<String, String> {
    let (_, gui_dir, project_root) = get_paths()?;
    let tmp_path = gui_dir.join("tmp_input.png");

    let image_bytes = general_purpose::STANDARD
        .decode(image_b64.replace("data:image/png;base64,", ""))
        .map_err(|e| e.to_string())?;

    fs::write(&tmp_path, image_bytes)
        .map_err(|e| format!("Failed to write temp PNG: {e}"))?;

    let script = gui_dir.join("run_model.py");
    let model = gui_dir.join("verifier1.pt");

    let python_path = project_root.join(".venv").join("bin").join("python");

    let output = Command::new(&python_path)
        .arg(&script)
        .arg(&tmp_path)
        .arg(&model)
        .output()
        .map_err(|e| format!("Failed to run AI script: {e}"))?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);

    if !output.status.success() {
    let err_msg = if stderr.trim().is_empty() {
        "Unknown error from AI script".to_string()
    } else {
        stderr.to_string()
    };
    return Err(format!("AI script error: {}", err_msg));
}

    if !output.status.success() {
        return Err(format!("AI script error: {}", stdout));
    }

    Ok(stdout.to_string())
}

// NEW: Load overlay image as base64
#[command]
fn load_overlay_image(image_path: String) -> Result<String, String> {
    let path = PathBuf::from(&image_path);
    
    if !path.exists() {
        return Err(format!("Overlay image not found: {}", image_path));
    }
    
    let bytes = fs::read(&path)
        .map_err(|e| format!("Failed to read overlay: {e}"))?;
    
    let b64 = general_purpose::STANDARD.encode(bytes);
    Ok(format!("data:image/png;base64,{}", b64))
}

#[command]
fn save_detection_json(
    data: SolarDetection,
    filename: String,
) -> Result<String, String> {
    let (_, _, project_root) = get_paths()?;
    
    let output_dir = project_root.join("detections");
    fs::create_dir_all(&output_dir).map_err(|e| e.to_string())?;
    
    let output_path = output_dir.join(&filename);
    
    let json_string = serde_json::to_string_pretty(&data)
        .map_err(|e| format!("Failed to serialize: {}", e))?;
    
    fs::write(&output_path, json_string)
        .map_err(|e| format!("Failed to write file: {}", e))?;
    
    Ok(output_path.to_string_lossy().to_string())
}

#[command]
fn save_batch_results(
    detections: Vec<SolarDetection>,
    batch_name: String,
) -> Result<String, String> {
    let (_, _, project_root) = get_paths()?;
    
    let output_dir = project_root.join("batch_results");
    fs::create_dir_all(&output_dir).map_err(|e| e.to_string())?;
    
    let timestamp = chrono::Local::now().format("%Y%m%d_%H%M%S");
    let filename = format!("{}_{}.json", batch_name, timestamp);
    let output_path = output_dir.join(&filename);
    
    let json_string = serde_json::to_string_pretty(&detections)
        .map_err(|e| format!("Failed to serialize: {}", e))?;
    
    fs::write(&output_path, json_string)
        .map_err(|e| format!("Failed to write file: {}", e))?;
    
    Ok(output_path.to_string_lossy().to_string())
}

#[command]
fn save_audit_overlay(
    image_path: String,
    sample_id: String,
) -> Result<String, String> {
    let (_, _, project_root) = get_paths()?;
    
    let output_dir = project_root.join("audit_overlays");
    fs::create_dir_all(&output_dir).map_err(|e| e.to_string())?;
    
    let timestamp = chrono::Local::now().format("%Y%m%d_%H%M%S");
    let filename = format!("audit_{}_{}.png", sample_id, timestamp);
    let output_path = output_dir.join(&filename);
    
    fs::copy(&image_path, &output_path)
        .map_err(|e| format!("Failed to copy audit overlay: {}", e))?;
    
    Ok(output_path.to_string_lossy().to_string())
}

#[command]
fn process_csv_batch(
    csv_path: String,
    zoom: u32,
    radius: u32,
    provider: String,
) -> Result<Vec<SolarDetection>, String> {
    use csv::ReaderBuilder;

    let mut reader = ReaderBuilder::new()
        .has_headers(true)
        .from_path(&csv_path)
        .map_err(|e| format!("Failed to read CSV: {}", e))?;
    
    let mut results = Vec::new();
    
    for result in reader.deserialize() {
        let row: CsvRow = result.map_err(|e| format!("Failed to parse row: {}", e))?;
        
        // Fetch tile
        let tile_b64 = fetch_stitched_tile(row.lat, row.lon, zoom, radius, provider.clone())?;
        
        // Run AI
        let ai_json = run_ai_analysis(tile_b64)?;
        
        // Parse only JSON line
        let json_line = ai_json
            .lines()
            .find(|line| line.trim().starts_with('{'))
            .ok_or("No JSON in AI output")?;
        
        let mut detection: SolarDetection = serde_json::from_str(json_line)
            .map_err(|e| format!("Failed to parse AI result: {}", e))?;
        
        detection.sample_id = row.sample_id;
        detection.lat = row.lat;
        detection.lon = row.lon;
        detection.zoom = zoom;
        detection.radius = radius;
        detection.provider = provider.clone();
        
        results.push(detection);
    }
    
    Ok(results)
}

#[command]
fn clear_tile_cache() -> Result<String, String> {
    let (_, gui_dir, _) = get_paths()?;
    let cache_dir = gui_dir.join("tile_cache");
    
    if cache_dir.exists() {
        fs::remove_dir_all(&cache_dir)
            .map_err(|e| format!("Failed to clear cache: {}", e))?;
    }
    
    Ok("Cache cleared successfully".to_string())
}

#[command]
fn get_cache_size() -> Result<u64, String> {
    let (_, gui_dir, _) = get_paths()?;
    let cache_dir = gui_dir.join("tile_cache");
    
    if !cache_dir.exists() {
        return Ok(0);
    }
    
    let mut total_size = 0u64;
    
    fn walk_dir(dir: &PathBuf, total: &mut u64) -> std::io::Result<()> {
        for entry in fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();
            if path.is_dir() {
                walk_dir(&path, total)?;
            } else {
                *total += entry.metadata()?.len();
            }
        }
        Ok(())
    }
    
    walk_dir(&cache_dir, &mut total_size).map_err(|e| e.to_string())?;
    
    Ok(total_size)
}

#[command]
fn add_to_training_data(detection: SolarDetection) -> Result<String, String> {
    let (_, gui_dir, _) = get_paths()?;
    let training_file = gui_dir.join("qc_training_data.json");
    
    let mut data = if training_file.exists() {
        let content = fs::read_to_string(&training_file).unwrap_or_else(|_| "[]".to_string());
        serde_json::from_str::<Vec<Value>>(&content).unwrap_or_default()
    } else {
        Vec::new()
    };
    
    let sample = json!({
        "timestamp": chrono::Local::now().to_rfc3339(),
        "confidence": detection.confidence,
        "panel_count": detection.panel_count_est,
        "area_sqm": detection.pv_area_sqm_est,
        "capacity_kw": detection.capacity_kw_est,
        "has_solar": detection.has_solar,
        "qc_notes": detection.qc_notes
    });
    
    data.push(sample);
    
    let json_string = serde_json::to_string_pretty(&data)
        .map_err(|e| format!("Serialization failed: {}", e))?;
    
    fs::write(&training_file, json_string)
        .map_err(|e| format!("Write failed: {}", e))?;
    
    Ok(format!("Sample #{} added", data.len()))
}


// ============================================================
// MAIN
// ============================================================

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            if let Some(win) = app.get_webview_window("main") {
                win.set_title("Helioscope - Solar Panel Detection")?;
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            fetch_and_crop_tile,
            fetch_stitched_tile,
            run_ai_analysis,
            load_overlay_image,
            save_detection_json,
            save_batch_results,
            save_audit_overlay,
            process_csv_batch,
            clear_tile_cache,
            get_cache_size
        ])
        .run(tauri::generate_context!())
        .expect("error while running Tauri app");
}
