import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
import pickle
import warnings

warnings.filterwarnings('ignore')

class TwoStageStressModel:
    def __init__(self, data_path):
        self.data_path = data_path
        self.df = None
        self.model_1_lifestyle = None
        self.model_2_stressors = None
        self.scaler_1 = StandardScaler()
        self.scaler_2 = StandardScaler()
        self.X_stressors_columns = None

    def load_and_prepare_data(self):
        print("📥 Loading and processing dataset for Split Architecture...")
        self.df = pd.read_excel(self.data_path)
        
        # ---------------------------------------------------------
        # COMPONENT 1: LIFESTYLE FEATURES (Physical Tax)
        # ---------------------------------------------------------
        self.X_lifestyle = pd.DataFrame()
        self.X_lifestyle['age'] = self.df['age']
        self.X_lifestyle['sleep_avg_hours'] = self.df['sleep_avg_hours']
        self.X_lifestyle['work_study_hours'] = self.df['work_study_hours']
        self.X_lifestyle['screen_time_hours'] = self.df['screen_time_hours']
        
        # Non-linear sleep features
        self.X_lifestyle['sleep_deviation'] = (self.df['sleep_avg_hours'] - 7.5).abs()
        self.X_lifestyle['oversleeping_risk'] = (self.df['sleep_avg_hours'] > 9.0).astype(int)
        
        # ---------------------------------------------------------
        # COMPONENT 2: STRESSOR FEATURES (Psychological Tax)
        # ---------------------------------------------------------
        self.df['primary_stressors'] = self.df['primary_stressors'].fillna('None').astype(str)
        
        # 1. Count the stressors
        self.X_stressors = pd.DataFrame()
        self.X_stressors['num_stressors'] = self.df['primary_stressors'].apply(lambda x: len(x.split(';')))
        
        # 2. One-Hot Encode every unique stressor seamlessly
        stressor_dummies = self.df['primary_stressors'].str.replace('; ', ';').str.get_dummies(sep=';')
        self.X_stressors = pd.concat([self.X_stressors, stressor_dummies], axis=1)
        
        # Save columns for inference export
        self.X_stressors_columns = list(self.X_stressors.columns)

        # Standardize features
        self.X_lifestyle_scaled = pd.DataFrame(
            self.scaler_1.fit_transform(self.X_lifestyle), 
            columns=self.X_lifestyle.columns
        )
        self.X_stressors_scaled = pd.DataFrame(
            self.scaler_2.fit_transform(self.X_stressors), 
            columns=self.X_stressors.columns
        )
        
        self.y = self.df['stress_score']
        
        # Split Data
        indices = np.arange(len(self.df))
        self.idx_train, self.idx_test, self.y_train, self.y_test = train_test_split(
            indices, self.y, test_size=0.2, random_state=42
        )
        print("✅ Data preparation complete!")

    def train_two_stage_model(self):
        print("\n" + "=" * 70)
        print("🚀 TRAINING STAGE 1: The Lifestyle Model")
        print("=" * 70)
        
        self.model_1_lifestyle = xgb.XGBRegressor(
            n_estimators=100, max_depth=4, learning_rate=0.05, 
            reg_lambda=2.0, random_state=42
        )
        
        X_train_L = self.X_lifestyle_scaled.iloc[self.idx_train]
        self.model_1_lifestyle.fit(X_train_L, self.y_train)
        
        m1_train_preds = self.model_1_lifestyle.predict(X_train_L)
        residuals_train = self.y_train - m1_train_preds
        
        print("✅ Stage 1 complete. Extracting residuals...")
        
        print("\n" + "=" * 70)
        print("🚀 TRAINING STAGE 2: The Stressor Model (Predicting Residuals)")
        print("=" * 70)
        
        self.model_2_stressors = xgb.XGBRegressor(
            n_estimators=150, max_depth=5, learning_rate=0.05,
            reg_alpha=1.0, random_state=42
        )
        
        X_train_S = self.X_stressors_scaled.iloc[self.idx_train]
        self.model_2_stressors.fit(X_train_S, residuals_train)
        print("✅ Stage 2 complete.")

    def evaluate(self):
        print("\n" + "=" * 70)
        print("📊 MODEL EVALUATION (TWO-STAGE ARCHITECTURE)")
        print("=" * 70)
        
        X_test_L = self.X_lifestyle_scaled.iloc[self.idx_test]
        X_test_S = self.X_stressors_scaled.iloc[self.idx_test]
        
        X_train_L = self.X_lifestyle_scaled.iloc[self.idx_train]
        X_train_S = self.X_stressors_scaled.iloc[self.idx_train]
        
        comp1_preds_test = self.model_1_lifestyle.predict(X_test_L)
        comp2_preds_test = self.model_2_stressors.predict(X_test_S)
        final_preds_test = comp1_preds_test + comp2_preds_test
        
        comp1_preds_train = self.model_1_lifestyle.predict(X_train_L)
        comp2_preds_train = self.model_2_stressors.predict(X_train_S)
        final_preds_train = comp1_preds_train + comp2_preds_train
        
        train_r2 = r2_score(self.y_train, final_preds_train)
        test_r2 = r2_score(self.y_test, final_preds_test)
        gap = train_r2 - test_r2
        test_mae = mean_absolute_error(self.y_test, final_preds_test)
        test_rmse = np.sqrt(mean_squared_error(self.y_test, final_preds_test))
        
        print("\n🎯 Test Set Performance:")
        print(f"  Train R² Score: {train_r2:.4f}")
        print(f"  Test R² Score:  {test_r2:.4f}")
        print(f"  MAE:            {test_mae:.2f}")
        print(f"  RMSE:           {test_rmse:.2f}")
        
        print(f"\n⚠️  Overfitting Analysis:")
        print(f"  Gap: {gap:.4f}")
        if gap < 0.05:
            print(f"  ✅ Excellent generalization!")
        elif gap < 0.10:
            print(f"  ✅ Good generalization")
        else:
            print(f"  ⚠️  Some overfitting (gap > 0.10)")
            
    def export_model(self):
        print("\n" + "=" * 70)
        print("💾 EXPORTING TWO-STAGE MODEL ARTIFACTS")
        print("=" * 70)
        
        # Save Scalers
        with open('stress_scaler_lifestyle.pkl', 'wb') as f:
            pickle.dump(self.scaler_1, f)
        print("  ✅ Saved: stress_scaler_lifestyle.pkl")
        
        with open('stress_scaler_stressors.pkl', 'wb') as f:
            pickle.dump(self.scaler_2, f)
        print("  ✅ Saved: stress_scaler_stressors.pkl")
        
        # Save Models
        self.model_1_lifestyle.save_model('stress_model_lifestyle.json')
        print("  ✅ Saved: stress_model_lifestyle.json")
        
        self.model_2_stressors.save_model('stress_model_stressors.json')
        print("  ✅ Saved: stress_model_stressors.json")
        
        # Save the exact stressor columns for inference mapping
        with open('stressor_columns.pkl', 'wb') as f:
            pickle.dump(self.X_stressors_columns, f)
        print("  ✅ Saved: stressor_columns.pkl (Crucial for Component 2 inference!)")
        
        print("\n🚀 Two-Stage Model successfully exported and ready for production!")

if __name__ == "__main__":
    model = TwoStageStressModel('synthetic_stress_data_realistic.xlsx')
    model.load_and_prepare_data()
    model.train_two_stage_model()
    model.evaluate()
    model.export_model()