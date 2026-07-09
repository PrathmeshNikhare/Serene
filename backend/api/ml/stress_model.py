import os
import sys
import pickle
import warnings
import pandas as pd
import xgboost as xgb
import shap
from typing import List, Dict, Tuple

# Ignore warnings
warnings.filterwarnings("ignore")

# Path helper to reference files in the /test directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKSPACE_ROOT = os.path.dirname(BASE_DIR)
TEST_DIR = os.path.join(WORKSPACE_ROOT, "test")

MODEL_PATH = os.path.join(TEST_DIR, "xgboost_stress_model.json")
ENCODER_PATH = os.path.join(TEST_DIR, "stressor_encoder.pkl")
FEATURES_PATH = os.path.join(TEST_DIR, "feature_columns.pkl")

# Lazy loading of assets to keep startup fast
_model = None
_mlb = None
_feature_columns = None
_explainer = None

def load_model_assets():
    global _model, _mlb, _feature_columns, _explainer
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")
        if not os.path.exists(ENCODER_PATH):
            raise FileNotFoundError(f"Encoder file not found at {ENCODER_PATH}")
        if not os.path.exists(FEATURES_PATH):
            raise FileNotFoundError(f"Features file not found at {FEATURES_PATH}")
            
        # Load XGBoost model
        _model = xgb.XGBRegressor()
        _model.load_model(MODEL_PATH)
        
        # Load MultiLabelBinarizer
        with open(ENCODER_PATH, "rb") as f:
            _mlb = pickle.load(f)
            
        # Load feature columns list
        with open(FEATURES_PATH, "rb") as f:
            _feature_columns = pickle.load(f)
            
        # Build SHAP TreeExplainer
        _explainer = shap.TreeExplainer(_model)

def predict_stress(
    age: int,
    gender: str,
    persona: str,
    sleep_avg_hours: float,
    screen_time_hours: float,
    work_study_hours: float,
    wellness_points: int,
    factors: List[str]
) -> Tuple[float, Dict[str, float]]:
    """
    Predict stress score and extract significant mathematical drivers using SHAP.
    
    Returns:
        (predicted_stress_score: float, top_drivers: Dict[str, float])
    """
    load_model_assets()
    
    # Map gender labels to model's expected column names
    gender_map = {
        "Female": "gender_Female",
        "Male": "gender_Male",
        "Non-binary": "gender_Non-binary"
    }
    
    # Initialize dictionary with base/numeric fields (floats required by pandas)
    live_user = {
        "age": float(age),
        "sleep_avg_hours": float(sleep_avg_hours),
        "screen_time_hours": float(screen_time_hours),
        "work_study_hours": float(work_study_hours),
        "wellness_points": float(wellness_points)
    }
    
    # Set the user's specific persona flags to 1.0 based on new categories
    if persona == "Exam Warrior/ Teenager":
        live_user["persona_Teen"] = 1.0
        live_user["persona_Exam Warrior"] = 1.0
    elif persona == "Corporate Professional":
        live_user["persona_Corporate"] = 1.0
    elif persona == "Parent of a teenager":
        live_user["persona_Parent"] = 1.0
    elif persona == "Working Woman":
        live_user["persona_Working Woman"] = 1.0
    # Bachelor maps to baseline, so no persona flags are set to 1.0
        
    # Set the user's gender flag to 1.0
    mapped_gender = gender_map.get(gender)
    if mapped_gender:
        live_user[mapped_gender] = 1.0
        
    # Binarize factors (stressors) using MultiLabelBinarizer
    # mlb.transform expects an iterable of iterables e.g. [factors]
    binarized = _mlb.transform([factors])[0]
    for class_name, val in zip(_mlb.classes_, binarized):
        live_user[class_name] = float(val)
        
    # Build DataFrame matching the exact feature columns order
    input_df = pd.DataFrame(0.0, index=[0], columns=_feature_columns)
    
    for key, value in live_user.items():
        if key in input_df.columns:
            input_df.loc[0, key] = float(value)
            
    # Run prediction
    predicted_score = float(_model.predict(input_df)[0])
    
    # Run SHAP to extract driver impacts
    shap_values = _explainer(input_df)
    shap_array = shap_values.values[0]
    
    feature_impacts = {}
    for feature, impact in zip(_feature_columns, shap_array):
        feature_impacts[feature] = float(impact)
        
    # Filter drivers that have a POSITIVE impact (v > 0) meaning they INCREASE stress
    increasing_drivers = {
        feature: round(float(impact), 3)
        for feature, impact in feature_impacts.items()
        if float(impact) > 0.01
    }
    
    # Sort them descending (largest impact first) and take the top 5
    top_5_drivers = dict(
        sorted(increasing_drivers.items(), key=lambda item: item[1], reverse=True)[:5]
    )
    
    return predicted_score, top_5_drivers

def get_all_factors() -> List[str]:
    """Get the full list of checkbox binarizer classes supported by the model."""
    load_model_assets()
    return list(_mlb.classes_)
