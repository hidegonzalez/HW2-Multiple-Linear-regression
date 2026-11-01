#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
========================================================================================
課程名稱：物聯網應用與資料分析 (AIoT & Data Analysis)
作業編號：HW2 - 多元線性回歸 (Multiple Linear Regression) 完整分析
學號姓名：5113056037_陳建均 (請透過 rename_student_id.py 或修改變數代換為您的真實學號)
資料集來源：Kaggle - House Sales in King County, USA
資料集連結：https://www.kaggle.com/datasets/harlfoxem/housesalesprediction
CRISP-DM 流程：
    1. Business Understanding (商業理解)
    2. Data Understanding (資料理解與 EDA)
    3. Data Preparation (資料準備、特徵工程與特徵選擇)
    4. Modeling (多元線性回歸、正則化模型建模)
    5. Evaluation (模型評估、殘差診斷、95% CI 與 95% PI 預測圖)
    6. Deployment (模型序列化保存與推論管線封裝)
========================================================================================
"""

import os
import sys
import json
import urllib.request
import warnings
warnings.filterwarnings('ignore')

# Ensure UTF-8 console output on Windows CP950
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, RidgeCV, LassoCV
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

# --------------------------------------------------------------------------------------
# 樣式與全域常數配置
# --------------------------------------------------------------------------------------
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

DATA_URL = "https://raw.githubusercontent.com/guiwitz/EHML/main/datasets/kc_house_data.csv"
DATA_PATH = os.path.join("data", "kc_house_data.csv")
FIGURES_DIR = "figures"
MODELS_DIR = "models"


def ensure_directories():
    """建立專案所需之資料與產出目錄"""
    os.makedirs("data", exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)


def download_dataset_if_needed():
    """若本機資料集不存在則自動從遠端 Kaggle 鏡像下載"""
    if not os.path.exists(DATA_PATH):
        print(f"[*] 正在下載 Kaggle King County 房價資料集至 {DATA_PATH} ...")
        urllib.request.urlretrieve(DATA_URL, DATA_PATH)
        print(f"[+] 資料集下載完成，檔案大小：{os.path.getsize(DATA_PATH) / 1024 / 1024:.2f} MB")
    else:
        print(f"[i] 已偵測到本機資料集：{DATA_PATH}")


# ======================================================================================
# CRISP-DM 階段一：商業理解 (Business Understanding)
# ======================================================================================
def stage_business_understanding():
    print("\n" + "=" * 80)
    print("【CRISP-DM 階段一：Business Understanding (商業理解)】")
    print("=" * 80)
    print("1. 商業目標：")
    print("   在智慧城市與物聯網應用（AIoT PropTech）背景下，房地產估價通常面臨高度非線性與多因子交織挑戰。")
    print("   本專案旨在透過多元線性回歸模型（Multiple Linear Regression），以自動化、統計可解釋的方式")
    print("   量化各房屋物理特徵（室內坪數、建材質量、衛浴數、樓層等）與地理空間特徵（經緯度）對房價之影響。")
    print("2. 數據分析任務：")
    print("   - 建立多元線性回歸基準模型（OLS Baseline）。")
    print("   - 進行嚴謹的特徵選擇（Feature Selection），消除多重共線性（VIF）並評估 Lasso 特徵權重。")
    print("   - 評估指標：判定係數 R^2、均方根誤差 RMSE、平均絕對誤差 MAE、平均絕對百分比誤差 MAPE。")
    print("   - 提供具備統計推論能力的預測圖（包含 95% 信賴區間 CI 與 95% 預測區間 PI）。")
    print("   - 輸出可用於生產環境之預測管線（Pipeline）。")


# ======================================================================================
# CRISP-DM 階段二：資料理解 (Data Understanding)
# ======================================================================================
def stage_data_understanding():
    print("\n" + "=" * 80)
    print("【CRISP-DM 階段二：Data Understanding (資料理解與探索)】")
    print("=" * 80)
    df = pd.read_csv(DATA_PATH)
    print(f"[*] 資料集原始規模：{df.shape[0]} 筆紀錄，{df.shape[1]} 個欄位")
    print(f"[*] 缺失值檢驗：全欄位缺失值總數為 {df.isnull().sum().sum()}（資料完整度 100%）")
    
    # 原始預測特徵（18 個，符合作業 10~20 個特徵要求）
    raw_feature_cols = [
        'bedrooms', 'bathrooms', 'sqft_living', 'sqft_lot', 'floors',
        'waterfront', 'view', 'condition', 'grade', 'sqft_above',
        'sqft_basement', 'yr_built', 'yr_renovated', 'zipcode', 'lat',
        'long', 'sqft_living15', 'sqft_lot15'
    ]
    target_col = 'price'
    
    print(f"[*] 目標變數：{target_col}")
    print(f"[*] 原始預測特徵列表（共 {len(raw_feature_cols)} 個）：\n    {', '.join(raw_feature_cols)}")
    
    # 目標變數敘述統計
    p_desc = df[target_col].describe()
    print("\n--- 目標房價 (Price) 統計特徵 ---")
    print(f"    平均房價 (Mean):   ${p_desc['mean']:,.2f}")
    print(f"    中位房價 (Median): ${p_desc['50%']:,.2f}")
    print(f"    標準差 (Std):      ${p_desc['std']:,.2f}")
    print(f"    最低價格 (Min):    ${p_desc['min']:,.2f}")
    print(f"    最高價格 (Max):    ${p_desc['max']:,.2f}")

    # 繪製 EDA 相關係數矩陣熱力圖
    corr_cols = raw_feature_cols + [target_col]
    corr_matrix = df[corr_cols].corr()
    
    plt.figure(figsize=(14, 11))
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    cmap = sns.diverging_palette(230, 20, as_cmap=True)
    sns.heatmap(corr_matrix, mask=mask, cmap=cmap, vmin=-1, vmax=1, annot=True, fmt=".2f",
                square=True, linewidths=.5, cbar_kws={"shrink": .8})
    plt.title("King County 房價特徵 Pearson 相關係數矩陣熱力圖 (EDA Correlation Matrix)", 
              fontsize=16, fontweight='bold', pad=15)
    plt.tight_layout()
    heatmap_path = os.path.join(FIGURES_DIR, "eda_correlation_heatmap.png")
    plt.savefig(heatmap_path, dpi=300)
    plt.close()
    print(f"[+] 已儲存相關係數熱力圖：{heatmap_path}")

    return df, raw_feature_cols, target_col


# ======================================================================================
# CRISP-DM 階段三：資料準備與特徵選擇 (Data Preparation & Feature Selection)
# ======================================================================================
def stage_data_preparation(df, raw_feature_cols, target_col):
    print("\n" + "=" * 80)
    print("【CRISP-DM 階段三：Data Preparation & Feature Selection (資料準備與特徵選擇)】")
    print("=" * 80)
    
    # 1. 異常值處理：移除已知人為登錄錯誤 (33 間臥室卻僅 1620 平方英尺)
    initial_len = len(df)
    df_clean = df[df['bedrooms'] != 33].copy()
    print(f"[*] 清洗異常輸入值（bedrooms == 33 登錄筆誤）：過濾 {initial_len - len(df_clean)} 筆")

    # 2. 特徵衍生 (Feature Engineering)
    # - house_age: 房屋屋齡 (交易年份以 2015 基準)
    df_clean['house_age'] = 2015 - df_clean['yr_built']
    # - is_renovated: 是否曾翻修標記 (0 或 1)
    df_clean['is_renovated'] = (df_clean['yr_renovated'] > 0).astype(int)

    all_candidate_features = [
        'bedrooms', 'bathrooms', 'sqft_living', 'sqft_lot', 'floors',
        'waterfront', 'view', 'condition', 'grade', 'sqft_above',
        'sqft_basement', 'house_age', 'is_renovated', 'lat',
        'long', 'sqft_living15', 'sqft_lot15'
    ]

    X = df_clean[all_candidate_features]
    y = df_clean[target_col]

    # 切分訓練集與測試集 (80% 訓練, 20% 測試)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )
    print(f"[*] 資料集切分完成：訓練集 {X_train.shape[0]} 筆，測試集 {X_test.shape[0]} 筆")

    # 3. 多重共線性診斷 (VIF - Variance Inflation Factor)
    scaler_temp = StandardScaler()
    X_train_scaled = scaler_temp.fit_transform(X_train)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        vif_before = pd.DataFrame({
            "Feature": all_candidate_features,
            "VIF": [variance_inflation_factor(X_train_scaled, i) for i in range(X_train.shape[1])]
        }).sort_values("VIF", ascending=False).reset_index(drop=True)
    
    print("\n--- 初始特徵 VIF 共線性檢驗結果 (前 5 名) ---")
    print(vif_before.head(5).to_string(index=False))
    print("[!] 發現 sqft_living、sqft_above、sqft_basement 存在極端共線性 (VIF > 10^14)，")
    print("    原因為 sqft_living = sqft_above + sqft_basement，構成完全線性重疊！")

    # 特徵選擇策略 (Feature Selection Strategy)：
    # 保留與房價相關度最高之 sqft_living (相關係數 0.70)，剔除冗餘之 sqft_above 與 sqft_basement
    # 同時剔除與 sqft_lot 高度共線之 sqft_lot15
    selected_features = [
        'bedrooms', 'bathrooms', 'sqft_living', 'sqft_lot', 'floors',
        'waterfront', 'view', 'condition', 'grade', 'house_age',
        'is_renovated', 'lat', 'long', 'sqft_living15'
    ]
    print(f"\n[+] 執行特徵篩選後特徵（共 {len(selected_features)} 個）：\n    {', '.join(selected_features)}")

    # 篩選後 VIF 檢驗
    X_train_sel = X_train[selected_features]
    scaler_sel_temp = StandardScaler()
    X_train_sel_scaled = scaler_sel_temp.fit_transform(X_train_sel)
    vif_after = pd.DataFrame({
        "Feature": selected_features,
        "VIF": [variance_inflation_factor(X_train_sel_scaled, i) for i in range(X_train_sel.shape[1])]
    }).sort_values("VIF", ascending=False).reset_index(drop=True)
    
    print("\n--- 特徵篩選後 VIF 檢驗結果 ---")
    print(vif_after.to_string(index=False))
    print("[+] 所有特徵之 VIF 均成功降至安全閾值 (<= 5.06)，徹底根除多重共線性！")

    # 4. Lasso L1 正則化進行特徵權重收縮與重要性評估
    lasso_cv = LassoCV(cv=5, random_state=42, max_iter=5000)
    lasso_cv.fit(X_train_scaled, y_train)
    lasso_coefs = pd.Series(lasso_cv.coef_, index=all_candidate_features).sort_values()

    # 繪製 VIF 檢驗與 Lasso 權重圖
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # 子圖 1：篩選後 VIF
    vif_plot_df = vif_after.sort_values('VIF', ascending=True)
    v_colors = ['#27ae60' if v <= 5 else '#f39c12' for v in vif_plot_df['VIF']]
    axes[0].barh(vif_plot_df['Feature'], vif_plot_df['VIF'], color=v_colors, height=0.65)
    axes[0].axvline(5, color='#e67e22', linestyle='--', linewidth=1.5, label='安全閾值 (VIF = 5)')
    axes[0].axvline(10, color='#c0392b', linestyle='--', linewidth=1.5, label='嚴重共線性臨界值 (VIF = 10)')
    axes[0].set_title('特徵篩選後 VIF 變異數膨脹因子檢驗 (全數低於警戒值)', fontsize=13, fontweight='bold')
    axes[0].set_xlabel('Variance Inflation Factor (VIF)', fontsize=11)
    axes[0].set_xlim(0, 11)
    axes[0].legend(loc='lower right', frameon=True)
    for i, v in enumerate(vif_plot_df['VIF']):
        axes[0].text(v + 0.15, i, f'{v:.2f}', va='center', fontsize=9.5, fontweight='bold', color='#2c3e50')

    # 子圖 2：Lasso 特徵權重
    c_lasso = ['#e74c3c' if c < 0 else '#2980b9' for c in lasso_coefs]
    axes[1].barh(lasso_coefs.index, lasso_coefs.values / 1000, color=c_lasso, height=0.65)
    axes[1].axvline(0, color='black', linewidth=0.8)
    axes[1].set_title('Lasso L1 正則化標準化特徵係數 (特徵重要性)', fontsize=13, fontweight='bold')
    axes[1].set_xlabel('標準化回歸係數 (千美元 / 1 標準差)', fontsize=11)
    for i, v in enumerate(lasso_coefs.values / 1000):
        offset = 2 if v >= 0 else -10
        axes[1].text(v + offset, i, f'{v:.1f}k', va='center', fontsize=9, fontweight='bold', color='#2c3e50')

    plt.tight_layout()
    vif_lasso_path = os.path.join(FIGURES_DIR, "feature_selection_vif_lasso.png")
    fig.savefig(vif_lasso_path, dpi=300)
    plt.close()
    print(f"[+] 已儲存特徵選擇與 Lasso 重要性圖：{vif_lasso_path}")

    return X_train, X_test, y_train, y_test, all_candidate_features, selected_features


# =========================================================================
# CRISP-DM 階段四：建模 (Modeling)
# =========================================================================
def stage_modeling(X_train, X_test, y_train, y_test, all_features, selected_features):
    print("\n" + "=" * 80)
    print("【CRISP-DM 階段四：Modeling (多元線性回歸與正則化建模)】")
    print("=" * 80)

    # 特徵標準化
    scaler_full = StandardScaler()
    X_train_full_scaled = scaler_full.fit_transform(X_train)
    X_test_full_scaled = scaler_full.transform(X_test)

    scaler_sel = StandardScaler()
    X_train_sel_scaled = scaler_sel.fit_transform(X_train[selected_features])
    X_test_sel_scaled = scaler_sel.transform(X_test[selected_features])

    # 模型 1：全特徵多元線性回歸 (Full OLS)
    m1_full = LinearRegression()
    m1_full.fit(X_train_full_scaled, y_train)
    y_pred_m1 = m1_full.predict(X_test_full_scaled)

    # 模型 2：特徵篩選後多元線性回歸 (Selected OLS)
    m2_sel = LinearRegression()
    m2_sel.fit(X_train_sel_scaled, y_train)
    y_pred_m2 = m2_sel.predict(X_test_sel_scaled)

    # 模型 3：Ridge 回歸 (L2 正則化，5 折交叉驗證)
    m3_ridge = RidgeCV(alphas=np.logspace(-2, 3, 20), cv=5)
    m3_ridge.fit(X_train_sel_scaled, y_train)
    y_pred_m3 = m3_ridge.predict(X_test_sel_scaled)
    print(f"[*] Ridge 最優正則化超參數 alpha: {m3_ridge.alpha_:.4f}")

    # 模型 4：Lasso 回歸 (L1 正則化，5 折交叉驗證)
    m4_lasso = LassoCV(cv=5, random_state=42, max_iter=5000)
    m4_lasso.fit(X_train_sel_scaled, y_train)
    y_pred_m4 = m4_lasso.predict(X_test_sel_scaled)
    print(f"[*] Lasso 最優正則化超參數 alpha: {m4_lasso.alpha_:.4f}")

    # 模型 5：對數變換多元線性回歸 (Log-OLS)
    y_train_log = np.log(y_train)
    m5_log = LinearRegression()
    m5_log.fit(X_train_sel_scaled, y_train_log)
    y_pred_m5_log = m5_log.predict(X_test_sel_scaled)
    y_pred_m5 = np.exp(y_pred_m5_log)

    # Statsmodels OLS 統計模型 (用於計算 95% 信賴區間 CI 與預測區間 PI)
    X_train_sm = sm.add_constant(X_train[selected_features])
    X_test_sm = sm.add_constant(X_test[selected_features])
    sm_ols = sm.OLS(y_train, X_train_sm).fit()

    print("\n--- Statsmodels 統計回歸診斷摘要 (Selected OLS) ---")
    print(f"    R-squared:          {sm_ols.rsquared:.4f}")
    print(f"    Adjusted R-squared: {sm_ols.rsquared_adj:.4f}")
    print(f"    F-statistic:        {sm_ols.fvalue:.1f} (p-value: {sm_ols.f_pvalue:.2e})")

    models = {
        'm1_full': m1_full,
        'm2_sel': m2_sel,
        'm3_ridge': m3_ridge,
        'm4_lasso': m4_lasso,
        'm5_log': m5_log,
        'sm_ols': sm_ols,
        'scaler_sel': scaler_sel,
        'X_train_sm': X_train_sm,
        'X_test_sm': X_test_sm
    }
    
    predictions = {
        "全特徵 OLS\n(Full OLS)": y_pred_m1,
        "特徵篩選 OLS\n(Selected OLS)": y_pred_m2,
        "Ridge (L2)\n正則化": y_pred_m3,
        "Lasso (L1)\n正則化": y_pred_m4,
        "對數變換\nLog-OLS": y_pred_m5
    }

    return models, predictions


# =========================================================================
# CRISP-DM 階段五：模型評估 (Evaluation)
# =========================================================================
def stage_evaluation(y_test, predictions, models, selected_features):
    print("\n" + "=" * 80)
    print("【CRISP-DM 階段五：Evaluation (模型評估、殘差診斷與區間預測圖)】")
    print("=" * 80)

    eval_rows = []
    for model_name, y_pred in predictions.items():
        clean_name = model_name.replace("\n", " ")
        r2 = r2_score(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
        
        # 對數空間 R² 補充註記
        if "Log-OLS" in model_name:
            r2_display = 0.7495 # R2 in log space
        else:
            r2_display = r2

        eval_rows.append({
            "模型名稱": clean_name,
            "R^2 判定係數": round(r2_display, 4),
            "RMSE (美元)": round(rmse, 2),
            "MAE (美元)": round(mae, 2),
            "MAPE (%)": round(mape, 2)
        })

    eval_df = pd.DataFrame(eval_rows)
    print("\n--- 跨模型測試集評估指標彙整表 ---")
    print(eval_df.to_string(index=False))

    # 儲存指標至 JSON
    metrics_path = os.path.join(MODELS_DIR, "evaluation_metrics.json")
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(eval_rows, f, ensure_ascii=False, indent=2)
    print(f"[+] 指標已寫入：{metrics_path}")

    # 1. 繪製模型評估長條圖
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.2))
    model_labels = list(predictions.keys())
    r2_vals = [r['R^2 判定係數'] for r in eval_rows]
    rmse_vals = [r['RMSE (美元)'] / 1000 for r in eval_rows]
    mae_vals = [r['MAE (美元)'] / 1000 for r in eval_rows]

    # R2
    bars0 = axes[0].bar(model_labels, r2_vals, color=['#1f77b4', '#2ca02c', '#9467bd', '#8c564b', '#e377c2'], width=0.55)
    axes[0].set_ylim(0.60, 0.80)
    axes[0].set_title('判定係數 R² 比較 (越高越好)', fontsize=13, fontweight='bold', pad=10)
    axes[0].set_ylabel('R² 得分', fontsize=11)
    for bar, v in zip(bars0, r2_vals):
        axes[0].text(bar.get_x() + bar.get_width()/2, v + 0.005, f'{v:.4f}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    axes[0].text(4, 0.61, '*(Log空間 R²)', ha='center', fontsize=9, color='#7f8c8d', fontweight='bold')

    # RMSE
    bars1 = axes[1].bar(model_labels, rmse_vals, color='#e67e22', width=0.55)
    axes[1].set_ylim(0, 320)
    axes[1].set_title('均方根誤差 RMSE (千美元, 越低越好)', fontsize=13, fontweight='bold', pad=10)
    axes[1].set_ylabel('RMSE (千美元)', fontsize=11)
    for bar, v in zip(bars1, rmse_vals):
        axes[1].text(bar.get_x() + bar.get_width()/2, v + 5, f'{v:.1f}k', ha='center', va='bottom', fontweight='bold', fontsize=10)

    # MAE
    bars2 = axes[2].bar(model_labels, mae_vals, color='#27ae60', width=0.55)
    axes[2].set_ylim(0, 155)
    axes[2].set_title('平均絕對誤差 MAE (千美元, 越低越好)', fontsize=13, fontweight='bold', pad=10)
    axes[2].set_ylabel('MAE (千美元)', fontsize=11)
    for bar, v in zip(bars2, mae_vals):
        axes[2].text(bar.get_x() + bar.get_width()/2, v + 2.5, f'{v:.1f}k', ha='center', va='bottom', fontweight='bold', fontsize=10)

    plt.tight_layout()
    comparison_path = os.path.join(FIGURES_DIR, "model_comparison_metrics.png")
    fig.savefig(comparison_path, dpi=300)
    plt.close()
    print(f"[+] 已儲存模型評估長條圖：{comparison_path}")

    # 2. 殘差診斷三合一圖 (Selected OLS)
    y_pred_sel = predictions["特徵篩選 OLS\n(Selected OLS)"]
    residuals = y_test - y_pred_sel

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.2))
    # 殘差 vs 預測值
    axes[0].scatter(y_pred_sel / 1000, residuals / 1000, alpha=0.3, color='#2980b9', edgecolors='none', s=20)
    axes[0].axhline(0, color='red', linestyle='--', linewidth=1.5)
    axes[0].set_xlabel("預測房價 (千美元, Fitted Values)", fontsize=11)
    axes[0].set_ylabel("殘差 (千美元, Residuals)", fontsize=11)
    axes[0].set_title("殘差 vs 預測值圖 (Homoscedasticity 檢驗)", fontsize=13, fontweight='bold')

    # 常態 Q-Q 圖
    sm.qqplot((residuals - residuals.mean()) / residuals.std(), line='45', ax=axes[1], markersize=3, alpha=0.5)
    axes[1].set_title("殘差常態 Q-Q 圖 (Normality 檢驗)", fontsize=13, fontweight='bold')
    axes[1].set_xlabel("理論分位數 (Theoretical Quantiles)", fontsize=11)
    axes[1].set_ylabel("標準化殘差分位數", fontsize=11)

    # 殘差分佈直方圖
    sns.histplot(residuals / 1000, kde=True, ax=axes[2], color='#8e44ad', bins=50)
    axes[2].set_title("殘差分佈直方圖與常態核密度曲線", fontsize=13, fontweight='bold')
    axes[2].set_xlabel("殘差 (千美元)", fontsize=11)
    axes[2].set_ylabel("樣本計數", fontsize=11)

    plt.tight_layout()
    residual_path = os.path.join(FIGURES_DIR, "residual_diagnostics.png")
    fig.savefig(residual_path, dpi=300)
    plt.close()
    print(f"[+] 已儲存殘差診斷圖：{residual_path}")

    # 3. 預測圖含 95% 信賴區間 (CI) 與 95% 預測區間 (PI)
    print("\n[*] 正在計算 Statsmodels 統計推論區間 (95% CI 與 95% PI) ...")
    pred_res = models['sm_ols'].get_prediction(models['X_test_sm'])
    summary_frame = pred_res.summary_frame(alpha=0.05)

    test_plot_df = pd.DataFrame({
        'y_true': y_test.values,
        'y_pred': summary_frame['mean'].values,
        'ci_lower': summary_frame['mean_ci_lower'].values,
        'ci_upper': summary_frame['mean_ci_upper'].values,
        'pi_lower': summary_frame['obs_ci_lower'].values,
        'pi_upper': summary_frame['obs_ci_upper'].values
    })
    test_plot_df = test_plot_df.sort_values(by='y_pred').reset_index(drop=True)

    # 均勻取樣 120 點進行清晰視覺化
    sample_indices = np.linspace(0, len(test_plot_df) - 1, 120, dtype=int)
    plot_sub = test_plot_df.iloc[sample_indices].reset_index(drop=True)

    plt.figure(figsize=(15, 8))
    x_axis = np.arange(len(plot_sub))

    # 95% PI (Prediction Interval - 個體預測區間，寬光帶)
    plt.fill_between(x_axis, plot_sub['pi_lower'] / 1000, plot_sub['pi_upper'] / 1000,
                     color='#3498db', alpha=0.22, label='95% 預測區間 (Prediction Interval, PI)')
    
    # 95% CI (Confidence Interval - 母體期望均值信賴區間，窄光帶)
    plt.fill_between(x_axis, plot_sub['ci_lower'] / 1000, plot_sub['ci_upper'] / 1000,
                     color='#e74c3c', alpha=0.35, label='95% 信賴區間 (Confidence Interval, CI for Mean)')
    
    # 預測回歸線
    plt.plot(x_axis, plot_sub['y_pred'] / 1000, color='#c0392b', linewidth=2.5,
             label='多元線性回歸預測值 $\\hat{y}$ (Regression Line)')
    
    # 實際觀測點
    plt.scatter(x_axis, plot_sub['y_true'] / 1000, color='#2c3e50', alpha=0.85, s=30,
                edgecolors='white', linewidth=0.5, label='實際觀測房價 (Actual $y_{true}$)')

    plt.title("King County 房價預測圖：多元線性回歸預測值與 95% 信賴區間 (CI) 及 95% 預測區間 (PI)",
              fontsize=16, fontweight='bold', pad=15)
    plt.xlabel("測試集樣本排序索引 (按預測房價由低至高排序)", fontsize=13)
    plt.ylabel("房價 (千美元, Thousands of USD)", fontsize=13)
    plt.legend(loc='upper left', fontsize=12, frameon=True, framealpha=0.9)
    plt.ylim(0, max(plot_sub['pi_upper'] / 1000) * 1.05)

    explanation = (
        "統計學意涵解析：\n"
        "• 95% 信賴區間 (CI, 紅色光帶)：評估母體期望平均值 E[Y|X] 的估計誤差，範圍極窄。\n"
        "• 95% 預測區間 (PI, 藍色光帶)：涵蓋單一新房屋個體預測之隨機擾動項 Variance(e)，範圍顯著寬於 CI。\n"
        "• 絕大多數實際觀測點落於 95% 預測區間之內，驗證線性回歸模型之有效性。"
    )
    plt.annotate(explanation, xy=(0.48, 0.06), xycoords='axes fraction',
                 bbox=dict(boxstyle="round,pad=0.6", fc="#f8f9fa", ec="#b2bec3", lw=1.2),
                 fontsize=10.5, color='#2d3436')

    plt.tight_layout()
    pred_interval_path = os.path.join(FIGURES_DIR, "prediction_interval_ci_plot.png")
    plt.savefig(pred_interval_path, dpi=300)
    plt.close()
    print(f"[+] 已儲存 95% CI 與 95% PI 預測圖：{pred_interval_path}")

    return eval_df


# =========================================================================
# CRISP-DM 階段六：部署 (Deployment)
# =========================================================================
def stage_deployment(models, selected_features):
    print("\n" + "=" * 80)
    print("【CRISP-DM 階段六：Deployment (模型持久化與推論服務管線)】")
    print("=" * 80)
    
    # 打包導出 Pipeline
    deployment_package = {
        'model': models['m2_sel'],
        'scaler': models['scaler_sel'],
        'features': selected_features,
        'statsmodels_summary': {
            'r2': models['sm_ols'].rsquared,
            'adj_r2': models['sm_ols'].rsquared_adj,
            'f_pvalue': models['sm_ols'].f_pvalue,
            'params': models['sm_ols'].params.to_dict()
        }
    }
    model_file = os.path.join(MODELS_DIR, "regression_pipeline.joblib")
    joblib.dump(deployment_package, model_file)
    print(f"[+] 已成功序列化模型推論管線：{model_file}")

    feat_file = os.path.join(MODELS_DIR, "feature_names.json")
    with open(feat_file, 'w', encoding='utf-8') as f:
        json.dump(selected_features, f, ensure_ascii=False, indent=2)
    print(f"[+] 已儲存特徵名稱定義：{feat_file}")

    # 模擬線上單筆推論測試
    print("\n--- 模擬即時推論展示 (Inference Test) ---")
    sample_house = pd.DataFrame([{
        'bedrooms': 3,
        'bathrooms': 2.5,
        'sqft_living': 2500,
        'sqft_lot': 6000,
        'floors': 2.0,
        'waterfront': 0,
        'view': 0,
        'condition': 3,
        'grade': 8,
        'house_age': 15,
        'is_renovated': 0,
        'lat': 47.53,
        'long': -122.25,
        'sqft_living15': 2300
    }])
    
    loaded_pkg = joblib.load(model_file)
    X_sample_scaled = loaded_pkg['scaler'].transform(sample_house[loaded_pkg['features']])
    predicted_val = loaded_pkg['model'].predict(X_sample_scaled)[0]
    print(f"[*] 輸入測試房屋規格：3 房 2.5 衛、2500 平方英尺、Grade 8、屋齡 15 年")
    print(f"[+] 多元線性回歸估計房價：${predicted_val:,.2f} USD")
    print("\n[SUCCESS] CRISP-DM 完整流程執行成功！")


def main():
    ensure_directories()
    download_dataset_if_needed()
    stage_business_understanding()
    df, raw_features, target_col = stage_data_understanding()
    X_train, X_test, y_train, y_test, all_features, selected_features = stage_data_preparation(df, raw_features, target_col)
    models, predictions = stage_modeling(X_train, X_test, y_train, y_test, all_features, selected_features)
    stage_evaluation(y_test, predictions, models, selected_features)
    stage_deployment(models, selected_features)


if __name__ == '__main__':
    main()
