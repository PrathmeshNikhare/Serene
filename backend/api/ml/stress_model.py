import os
import pickle
import warnings
import pandas as pd
import numpy as np
import xgboost as xgb
import shap
from typing import List, Dict, Tuple

# Ignore warnings
warnings.filterwarnings("ignore")

# Path helper to reference files in the /test directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKSPACE_ROOT = os.path.dirname(BASE_DIR)
TEST_DIR = os.path.join(WORKSPACE_ROOT, "test")

MODEL_LIFESTYLE_PATH = os.path.join(TEST_DIR, "stress_model_lifestyle.json")
MODEL_STRESSORS_PATH = os.path.join(TEST_DIR, "stress_model_stressors.json")
SCALER_LIFESTYLE_PATH = os.path.join(TEST_DIR, "stress_scaler_lifestyle.pkl")
SCALER_STRESSORS_PATH = os.path.join(TEST_DIR, "stress_scaler_stressors.pkl")
COLUMNS_STRESSORS_PATH = os.path.join(TEST_DIR, "stressor_columns.pkl")

# Lazy loading of assets to keep startup fast
_model_lifestyle = None
_model_stressors = None
_scaler_lifestyle = None
_scaler_stressors = None
_explainer_lifestyle = None
_explainer_stressors = None
_stressor_columns = None
_feature_names_lifestyle = None

def load_model_assets():
    global _model_lifestyle, _model_stressors, _scaler_lifestyle, _scaler_stressors
    global _explainer_lifestyle, _explainer_stressors, _stressor_columns, _feature_names_lifestyle
    
    if _model_lifestyle is None:
        if not os.path.exists(MODEL_LIFESTYLE_PATH):
            raise FileNotFoundError(f"Model file not found at {MODEL_LIFESTYLE_PATH}")
            
        # Load XGBoost models
        _model_lifestyle = xgb.XGBRegressor()
        _model_lifestyle.load_model(MODEL_LIFESTYLE_PATH)
        
        _model_stressors = xgb.XGBRegressor()
        _model_stressors.load_model(MODEL_STRESSORS_PATH)
        
        # Load Scalers
        with open(SCALER_LIFESTYLE_PATH, "rb") as f:
            _scaler_lifestyle = pickle.load(f)
            
        with open(SCALER_STRESSORS_PATH, "rb") as f:
            _scaler_stressors = pickle.load(f)
            
        # Load Stressor Columns
        with open(COLUMNS_STRESSORS_PATH, "rb") as f:
            _stressor_columns = pickle.load(f)
            
        _feature_names_lifestyle = getattr(_scaler_lifestyle, "feature_names_in_", ['age', 'sleep_avg_hours', 'work_study_hours', 'screen_time_hours', 'sleep_deviation', 'oversleeping_risk'])
            
        # Build SHAP TreeExplainers
        _explainer_lifestyle = shap.TreeExplainer(_model_lifestyle)
        _explainer_stressors = shap.TreeExplainer(_model_stressors)

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
    
    # ---------------------------------------------------------
    # COMPONENT 1: LIFESTYLE FEATURES
    # ---------------------------------------------------------
    features_lifestyle = {}
    features_lifestyle['age'] = float(age)
    features_lifestyle['sleep_avg_hours'] = float(sleep_avg_hours)
    features_lifestyle['work_study_hours'] = float(work_study_hours)
    features_lifestyle['screen_time_hours'] = float(screen_time_hours)
    features_lifestyle['sleep_deviation'] = abs(features_lifestyle['sleep_avg_hours'] - 7.5)
    features_lifestyle['oversleeping_risk'] = 1.0 if features_lifestyle['sleep_avg_hours'] > 9.0 else 0.0
    
    input_df_lifestyle = pd.DataFrame(0.0, index=[0], columns=_feature_names_lifestyle)
    for key, value in features_lifestyle.items():
        if key in input_df_lifestyle.columns:
            input_df_lifestyle.loc[0, key] = float(value)
            
    X_lifestyle_scaled = pd.DataFrame(_scaler_lifestyle.transform(input_df_lifestyle), columns=_feature_names_lifestyle)
    pred_lifestyle = float(_model_lifestyle.predict(X_lifestyle_scaled)[0])
    
    # ---------------------------------------------------------
    # COMPONENT 2: STRESSOR FEATURES
    # ---------------------------------------------------------
    input_df_stressors = pd.DataFrame(0.0, index=[0], columns=_stressor_columns)
    
    # 1. Count stressors
    num_stressors = float(len(factors) if factors else 1)
    if 'num_stressors' in input_df_stressors.columns:
        input_df_stressors.loc[0, 'num_stressors'] = num_stressors
        
    # 2. One-hot encode stressors based on EXACT columns trained
    if factors:
        for factor in factors:
            if factor in input_df_stressors.columns:
                input_df_stressors.loc[0, factor] = 1.0
                
    X_stressors_scaled = pd.DataFrame(_scaler_stressors.transform(input_df_stressors), columns=_stressor_columns)
    pred_stressors = float(_model_stressors.predict(X_stressors_scaled)[0])
    
    # ---------------------------------------------------------
    # FINAL PREDICTION
    # ---------------------------------------------------------
    final_pred = pred_lifestyle + pred_stressors
    
    # ---------------------------------------------------------
    # SHAP ANALYSIS
    # ---------------------------------------------------------
    shap_lifestyle = _explainer_lifestyle(X_lifestyle_scaled)
    shap_stressors = _explainer_stressors(X_stressors_scaled)
    
    feature_impacts = {}
    
    for feature, impact in zip(_feature_names_lifestyle, shap_lifestyle.values[0]):
        feature_impacts[feature] = float(impact)
        
    for feature, impact in zip(_stressor_columns, shap_stressors.values[0]):
        # Keep them separate if there are name collisions, but there shouldn't be
        feature_impacts[feature] = float(impact)
        
    increasing_drivers = {
        feature: round(float(impact), 3)
        for feature, impact in feature_impacts.items()
        if float(impact) > 0.01
    }
    
    top_5_drivers = dict(
        sorted(increasing_drivers.items(), key=lambda item: item[1], reverse=True)[:5]
    )
    
    print("\n" + "="*40)
    print("🧠 ML TWO-STAGE STRESS PREDICTION")
    print("="*40)
    print(f"Lifestyle Score (Base):  {pred_lifestyle:.2f}")
    print(f"Stressors Score (Resid): {pred_stressors:.2f}")
    print(f"Final Predicted Stress:  {final_pred:.2f}")
    print("Top 5 Drivers:")
    for driver, impact in top_5_drivers.items():
        print(f"  • {driver}: +{impact:.3f}")
    print("="*40 + "\n")
    
    return final_pred, top_5_drivers

def get_all_factors() -> List[str]:
    """Get the full list of stressor columns supported by the model."""
    load_model_assets()
    if _stressor_columns:
        # Filter out 'num_stressors' which is just a count feature, not a category
        return [c for c in _stressor_columns if c != 'num_stressors']
    return []
