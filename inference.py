"""
Inference
Trains a lightweight model on your detection data
Uses TinyLM approach for local inference
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict
import pickle

class Model:
    """
    Lightweight QC notes generator trained on solar panel detection data.
    Uses pattern matching + rule engine + learned weights.
    """
    
    def __init__(self, model_path: str = "solar_qc_model.pkl"):
        self.model_path = model_path
        self.weights = {}
        self.patterns = {}
        self.is_trained = False
        
        # Try to load existing model
        if Path(model_path).exists():
            self.load_model()
    
    def train(self, training_data: List[Dict]):
        """
        Train model on labeled QC data.
        
        training_data format:
        [
            {
                "confidence": 0.85,
                "panel_count": 12,
                "area_sqm": 45.2,
                "capacity_kw": 9.3,
                "has_solar": True,
                "qc_notes": [
                    "high confidence detection",
                    "clear roof view",
                    "distinct module grid"
                ]
            },
            ...
        ]
        """
        print(f"[Training] Starting with {len(training_data)} samples...")
        
        # Learn patterns from training data
        self.patterns = self._extract_patterns(training_data)
        
        # Learn confidence thresholds
        confidences = [d['confidence'] for d in training_data if d['has_solar']]
        self.weights['conf_high'] = np.percentile(confidences, 75) if confidences else 0.8
        self.weights['conf_medium'] = np.percentile(confidences, 50) if confidences else 0.65
        self.weights['conf_low'] = np.percentile(confidences, 25) if confidences else 0.5
        
        # Learn panel count thresholds
        counts = [d['panel_count'] for d in training_data if d['panel_count'] > 0]
        self.weights['count_large'] = np.percentile(counts, 75) if counts else 20
        self.weights['count_medium'] = np.percentile(counts, 50) if counts else 10
        
        # Learn area thresholds
        areas = [d['area_sqm'] for d in training_data if d['area_sqm'] > 0]
        self.weights['area_large'] = np.percentile(areas, 75) if areas else 100
        self.weights['area_medium'] = np.percentile(areas, 50) if areas else 50
        
        self.is_trained = True
        print(f"[Training] Model trained successfully!")
        print(f"[Weights] Confidence thresholds: {self.weights}")
        
        # Save model
        self.save_model()
    
    def _extract_patterns(self, training_data: List[Dict]) -> Dict:
        """Extract common QC note patterns from training data"""
        patterns = {
            'confidence': {},
            'size': {},
            'view': {},
            'grid': {}
        }
        
        for item in training_data:
            conf = item['confidence']
            count = item['panel_count']
            notes = item.get('qc_notes', [])
            
            # Map ranges to notes
            if conf > 0.8:
                for note in notes:
                    if 'confidence' in note.lower() or 'high' in note.lower():
                        patterns['confidence'][note] = patterns['confidence'].get(note, 0) + 1
            
            if count > 10:
                for note in notes:
                    if 'large' in note.lower() or 'commercial' in note.lower():
                        patterns['size'][note] = patterns['size'].get(note, 0) + 1
            
            for note in notes:
                if 'roof' in note.lower() or 'view' in note.lower():
                    patterns['view'][note] = patterns['view'].get(note, 0) + 1
                if 'grid' in note.lower() or 'module' in note.lower():
                    patterns['grid'][note] = patterns['grid'].get(note, 0) + 1
        
        return patterns
    
    def generate_notes(self, detection_data: Dict) -> List[str]:
        """
        Generate QC notes for a detection.
        
        detection_data:
        {
            "confidence": 0.85,
            "panel_count": 12,
            "area_sqm": 45.2,
            "capacity_kw": 9.3,
            "has_solar": True
        }
        """
        if not self.is_trained:
            return self._generate_rule_based_notes(detection_data)
        
        return self._generate_learned_notes(detection_data)
    

    
    def _generate_rule_based_notes(self, data: Dict) -> List[str]:
        """Fallback rule-based notes when untrained"""
        notes = []
        conf = data['confidence']
        count = data['panel_count']
        area = data['area_sqm']
        
        if conf > 0.85:
            notes.append("high confidence detection")
        elif conf > 0.65:
            notes.append("moderate confidence detection")
        else:
            notes.append("low confidence - needs verification")
        
        if conf > 0.75:
            notes.append("clear roof view")
        else:
            notes.append("obscured or unclear view")
        
        if count > 15:
            notes.append("large commercial installation")
        elif count > 5:
            notes.append("residential system detected")
        
        if count > 3 and conf > 0.6:
            notes.append("distinct module grid visible")
        
        if area > 50:
            notes.append("significant panel area coverage")
        
        return notes[:5]
    
    def save_model(self):
        """Save trained model to disk"""
        model_dict = {
            'weights': self.weights,
            'patterns': self.patterns,
            'is_trained': self.is_trained
        }
        with open(self.model_path, 'wb') as f:
            pickle.dump(model_dict, f)
        print(f"[Model] Saved to {self.model_path}")
    
    def load_model(self):
        """Load model from disk"""
        try:
            with open(self.model_path, 'rb') as f:
                model_dict = pickle.load(f)
            self.weights = model_dict['weights']
            self.patterns = model_dict['patterns']
            self.is_trained = model_dict['is_trained']
            print(f"[Model] Loaded from {self.model_path}")
        except Exception as e:
            print(f"[Warning] Could not load model: {e}")
            self.is_trained = False

# Global model instance
_model = Model()

def generate_qc_notes(detection_data: Dict) -> List[str]:
    """Public API for generating QC notes"""
    return _model.generate_notes(detection_data)

def train_model_from_file(json_file: str):
    """Train model from JSON file of labeled data"""
    with open(json_file, 'r') as f:
        training_data = json.load(f)
    _model.train(training_data)

def train_model_from_list(training_data: List[Dict]):
    """Train model from Python list"""
    _model.train(training_data)

def main():
    """CLI interface"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python ai_notes_generator.py train <json_file>")
        print("  python ai_notes_generator.py predict '<json_data>'")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "train" and len(sys.argv) > 2:
        train_model_from_file(sys.argv[2])
    
    elif cmd == "predict" and len(sys.argv) > 2:
        data = json.loads(sys.argv[2])
        notes = generate_qc_notes(data)
        print(notes)
        print(json.dumps(notes, indent=2))
    
    else:
        print("Unknown command or missing arguments")
        sys.exit(1)

if __name__ == "__main__":
    main()
