import json
import pickle
import xgboost as xgb
import shap
import pandas as pd

# 1. Load the assets you just trained
model = xgb.XGBRegressor()
model.load_model('D:/Prathamesh/Coding/Projects/Mental Health/test/xgboost_stress_model.json')

with open('D:/Prathamesh/Coding/Projects/Mental Health/test/stressor_encoder.pkl', 'rb') as f:
    mlb = pickle.load(f)

with open('D:/Prathamesh/Coding/Projects/Mental Health/test/feature_columns.pkl', 'rb') as f:
    feature_columns = pickle.load(f)

explainer = shap.TreeExplainer(model)

# 2. Simulate a live user input coming in
live_user = {
    "age": 18,
    "sleep_avg_hours": 4.0,
    "screen_time_hours": 7.0,
    "work_study_hours": 8.0,
    "wellness_points": 56,
    "persona_Exam Warrior": 1, 
    "Exam Anxiety": 1,          
    "Fear of Failure": 1,
    "Burnout": 1
}

# 3. Format into a DataFrame matching the model's layout
input_df = pd.DataFrame(0, index=[0], columns=feature_columns)
for key, value in live_user.items():
    if key in input_df.columns:
        input_df[key] = value

# 4. Predict score & extract SHAP mathematical drivers
predicted_score = model.predict(input_df)[0]
shap_values = explainer(input_df)

feature_impacts = dict(zip(input_df.columns, shap_values[0].values))

# ================= FIX IS HERE =================
# Filter: Keep ONLY drivers that have a POSITIVE impact (v > 0) meaning they INCREASE stress
increasing_drivers = {
    k: round(float(v), 3)
    for k, v in feature_impacts.items()
    if float(v) > 0.01
}

# Sort them descending (largest impact first) and take the top 5
top_5_increasing_drivers = dict(
    sorted(increasing_drivers.items(), key=lambda item: item[1], reverse=True)[:5]
)
# ===============================================

# 5. Build the text prompt payload
ml_payload = {
    "predicted_stress_score": round(float(predicted_score), 2),
    "top_5_stress_escalators": top_5_increasing_drivers
}

print("--- Data prepared for LLM Agent (Fixed Top 5 Escalators Only) ---")
print(json.dumps(ml_payload, indent=2))