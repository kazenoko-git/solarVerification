"""
Utility to collect and manage training data for the QC model
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

class TrainingDataManager:
    """Manages labeled training data collection"""
    
    def __init__(self, data_file: str = "qc_training_data.json"):
        self.data_file = data_file
        self.data = self._load_or_create()
    
    def _load_or_create(self) -> List[Dict]:
        """Load existing training data or create new"""
        if Path(self.data_file).exists():
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return []
    
    def add_sample(self, detection_result: Dict, qc_notes: List[str]):
        """
        Add a labeled sample to training data.
        
        detection_result: output from YOLO model
        qc_notes: human-verified QC notes
        """
        sample = {
            "timestamp": datetime.now().isoformat(),
            "confidence": detection_result['confidence'],
            "panel_count": detection_result['panel_count_est'],
            "area_sqm": detection_result['pv_area_sqm_est'],
            "capacity_kw": detection_result['capacity_kw_est'],
            "has_solar": detection_result['has_solar'],
            "qc_notes": qc_notes
        }
        self.data.append(sample)
        self.save()
        print(f"[Training] Added sample #{len(self.data)}")
    
    def add_batch(self, samples: List[Dict]):
        """Add multiple samples at once"""
        for sample in samples:
            self.data.append(sample)
        self.save()
        print(f"[Training] Added {len(samples)} samples. Total: {len(self.data)}")
    
    def save(self):
        """Save training data to file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def get_stats(self) -> Dict:
        """Get statistics on training data"""
        if not self.data:
            return {"total_samples": 0}
        
        has_solar = sum(1 for d in self.data if d['has_solar'])
        
        return {
            "total_samples": len(self.data),
            "has_solar": has_solar,
            "no_solar": len(self.data) - has_solar,
            "avg_confidence": sum(d['confidence'] for d in self.data) / len(self.data),
            "avg_panel_count": sum(d['panel_count'] for d in self.data if d['has_solar']) / max(has_solar, 1),
            "avg_area_sqm": sum(d['area_sqm'] for d in self.data if d['has_solar']) / max(has_solar, 1),
        }
    
    def get_data(self) -> List[Dict]:
        """Get all training data"""
        return self.data
    
    def export_csv(self, csv_file: str):
        """Export to CSV for analysis"""
        import csv
        
        if not self.data:
            print("No data to export")
            return
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['confidence', 'panel_count', 'area_sqm', 'capacity_kw', 'has_solar', 'qc_notes'])
            writer.writeheader()
            for sample in self.data:
                row = {k: v for k, v in sample.items() if k != 'timestamp'}
                row['qc_notes'] = '; '.join(sample['qc_notes'])
                writer.writerow(row)
        
        print(f"[Export] Saved to {csv_file}")

def main():
    """CLI for managing training data"""
    import sys
    
    manager = TrainingDataManager()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python training_data_builder.py stats")
        print("  python training_data_builder.py export <csv_file>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "stats":
        stats = manager.get_stats()
        print(json.dumps(stats, indent=2))
    
    elif cmd == "export" and len(sys.argv) > 2:
        manager.export_csv(sys.argv[2])
    
    else:
        print("Unknown command")
        sys.exit(1)

if __name__ == "__main__":
    main()
