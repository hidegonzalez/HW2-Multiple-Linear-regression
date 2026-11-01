#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AIoT HW2 - 多元線性回歸互動式 Web 分析平台後端 (Flask Web Server & REST API)
支援功能：
  1. 下拉選單切換多種問題 (Kaggle King County 房價 18 特徵, Kaggle 洪水預測 20 特徵, 50 Startups)
  2. 任意輸入資料集 URL (如 https://raw.githubusercontent.com/.../50_Startups.csv) 或上傳本地 CSV
  3. 完整 CRISP-DM 流程展示 (商業理解、資料理解、資料準備與特徵選擇、建模、評估、部署即時推論)
  4. 包含 95% 信賴區間 (CI) 與 95% 預測區間 (PI) 預測圖及殘差診斷
"""

import os
import io
import json
import urllib.request
import traceback
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, RidgeCV, LassoCV
from sklearn.feature_selection import SelectKBest, f_regression
from statsmodels.stats.outliers_influence import variance_inflation_factor
import warnings
import statsmodels.api as sm

app = Flask(__name__, static_folder='.', static_url_path='')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# 預設儲存的資料集路徑
DATASET_PRESETS = {
    'king_county': {
        'name': 'Kaggle: King County 房價預測 (18 個特徵)',
        'description': '美國西雅圖 2014-2015 房屋銷售數據，包含 18 項預測特徵與 1 項目標變數 (price)。',
        'file': os.path.join(DATA_DIR, 'kc_house_data.csv'),
        'default_target': 'price',
        'drop_cols': ['id', 'date']
    },
    'flood_prediction': {
        'name': 'Kaggle: Flood Prediction 洪水機率預測 (20 個特徵)',
        'description': 'Kaggle Playground Series s4e5 競賽資料，包含 20 項環境/基礎設施數值特徵與連續機率目標 (FloodProbability)。',
        'file': os.path.join(DATA_DIR, 'flood_prediction.csv'),
        'default_target': 'FloodProbability',
        'drop_cols': ['id']
    },
    '50_startups': {
        'name': '經典基準：50 Startups 創投利潤資料集 (4 個特徵)',
        'description': '50 家初創企業研發、行政與行銷支出與利潤資料 (連續目標 Profit)。',
        'file': os.path.join(DATA_DIR, '50_Startups.csv'),
        'default_target': 'Profit',
        'drop_cols': []
    }
}

# 全域快取最近訓練的模型與資料
CURRENT_MODEL = {
    'stats_model': None,
    'sklearn_model': None,
    'scaler': None,
    'feature_cols': [],
    'target_col': '',
    'train_means': {},
    'train_mins': {},
    'train_maxs': {}
}


def load_dataframe_from_source(source_type, source_val):
    """從不同來源載入 DataFrame，具備完善防呆與異常格式檢查機制"""
    if source_type == 'preset':
        if source_val not in DATASET_PRESETS:
            raise ValueError(f"未知的預設問題資料集識別碼：{source_val}")
        preset = DATASET_PRESETS[source_val]
        if not os.path.exists(preset['file']):
            raise FileNotFoundError(f"伺服器端找不到預設資料集檔案：{preset['file']}")
        try:
            df = pd.read_csv(preset['file'])
        except Exception as e:
            raise ValueError(f"預設資料集讀取失敗：{str(e)}")
            
        for col in preset.get('drop_cols', []):
            if col in df.columns:
                df = df.drop(columns=[col])
        return df, preset['default_target'], preset['name'], preset['description']
    
    elif source_type == 'url':
        url = str(source_val).strip()
        if not (url.startswith('http://') or url.startswith('https://')):
            raise ValueError("【防呆警告】網址格式錯誤！URL 必須以 http:// 或 https:// 開頭。")
        
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                content = response.read()
        except urllib.error.HTTPError as e:
            raise ValueError(f"【連線異常】無法自該網址下載檔案 (HTTP 狀態碼 {e.code})，請確認連結是否正確且公開可存取。")
        except urllib.error.URLError as e:
            raise ValueError(f"【連線逾時/失敗】無法連線至遠端伺服器 ({e.reason})，請確認網路環境與網址拼字。")
        except Exception as e:
            raise ValueError(f"【下載失敗】網路下載過程發生未知錯誤：{str(e)}")
            
        try:
            df = pd.read_csv(io.BytesIO(content))
        except pd.errors.EmptyDataError:
            raise ValueError("【檔案內容異常】下載的 CSV 檔案內容為空，無法進行分析！")
        except Exception as e:
            raise ValueError(f"【解析失敗】無法將該網址內容解析為 CSV 表格：{str(e)}")
            
        if len(df) == 0:
            raise ValueError("【防呆警告】該資料集樣本數為 0，無法進行回歸分析！")
            
        name = f"線上自訂資料集 ({os.path.basename(url.split('?')[0])})"
        desc = f"從線上 URL 成功載入：{url} (共 {len(df)} 筆樣本、{len(df.columns)} 欄位)"
        target = df.columns[-1]
        return df, target, name, desc

    elif source_type == 'upload':
        file_storage = source_val
        filename = getattr(file_storage, 'filename', '')
        if not filename or not filename.lower().endswith(('.csv', '.txt')):
            raise ValueError("【防呆警告】僅支援 CSV 格式檔案 (.csv)！請檢查上傳檔案的副檔名。")
            
        try:
            df = pd.read_csv(file_storage)
        except pd.errors.EmptyDataError:
            raise ValueError("【檔案內容異常】上傳的 CSV 檔案為空檔案！")
        except Exception as e:
            raise ValueError(f"【解析失敗】無法讀取上傳之 CSV 檔案：{str(e)}")
            
        if len(df) == 0:
            raise ValueError("【防呆警告】上傳檔案中無任何資料列！")
            
        name = f"本機上傳檔案 ({filename})"
        desc = f"由使用者自本機上傳之資料集，成功解析 {len(df)} 筆資料、{len(df.columns)} 欄位。"
        target = df.columns[-1]
        return df, target, name, desc
    else:
        raise ValueError(f"不支援的資料來源類別：{source_type}")


@app.route('/')
def index():
    """首頁返回 index.html"""
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/<path:path>')
def static_files(path):
    """靜態檔案服務"""
    return send_from_directory(BASE_DIR, path)


@app.route('/api/presets', methods=['GET'])
def get_presets():
    """獲取可用的內建問題/資料集清單 (加分要求 1)"""
    presets_list = []
    for k, v in DATASET_PRESETS.items():
        presets_list.append({
            'key': k,
            'name': v['name'],
            'description': v['description'],
            'default_target': v['default_target']
        })
    return jsonify({
        'status': 'success',
        'presets': presets_list,
        'example_custom_url': 'https://raw.githubusercontent.com/Avik-Jain/100-Days-Of-ML-Code/master/datasets/50_Startups.csv'
    })


@app.route('/api/load-dataset', methods=['POST'])
def api_load_dataset():
    """載入資料集並回傳基本統計資訊 (加分要求 1 & 2)"""
    try:
        if request.content_type and 'multipart/form-data' in request.content_type:
            source_type = request.form.get('source_type', 'upload')
            if 'file' not in request.files:
                return jsonify({'status': 'error', 'message': '未上傳檔案'}), 400
            file_storage = request.files['file']
            df, target_col, name, desc = load_dataframe_from_source('upload', file_storage)
        else:
            data = request.get_json() or {}
            source_type = data.get('source_type', 'preset')
            source_val = data.get('source_val', 'king_county')
            df, target_col, name, desc = load_dataframe_from_source(source_type, source_val)

        # 欄位分析
        cols_info = []
        numeric_cols = []
        categorical_cols = []
        
        for col in df.columns:
            dtype_str = str(df[col].dtype)
            is_num = pd.api.types.is_numeric_dtype(df[col])
            null_count = int(df[col].isnull().sum())
            if is_num:
                numeric_cols.append(col)
                cols_info.append({
                    'name': col,
                    'type': dtype_str,
                    'is_numeric': True,
                    'missing': null_count,
                    'mean': float(df[col].mean()) if len(df) > 0 else 0,
                    'std': float(df[col].std()) if len(df) > 0 else 0,
                    'min': float(df[col].min()) if len(df) > 0 else 0,
                    'max': float(df[col].max()) if len(df) > 0 else 0
                })
            else:
                categorical_cols.append(col)
                cols_info.append({
                    'name': col,
                    'type': dtype_str,
                    'is_numeric': False,
                    'missing': null_count,
                    'unique_count': int(df[col].nunique())
                })

        candidate_features = [c for c in numeric_cols if c != target_col]
        preview_records = df.head(5).to_dict(orient='records')
        
        temp_path = os.path.join(DATA_DIR, '_current_session.csv')
        df.to_csv(temp_path, index=False)

        return jsonify({
            'status': 'success',
            'dataset_name': name,
            'description': desc,
            'rows_count': int(len(df)),
            'cols_count': int(len(df.columns)),
            'target_col': target_col if target_col in df.columns else (numeric_cols[-1] if numeric_cols else ''),
            'numeric_cols': numeric_cols,
            'categorical_cols': categorical_cols,
            'candidate_features': candidate_features,
            'cols_info': cols_info,
            'preview': preview_records
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/train', methods=['POST'])
def api_train():
    """執行多元線性回歸訓練、特徵選擇、殘差診斷與區間估計"""
    try:
        data = request.get_json() or {}
        temp_path = os.path.join(DATA_DIR, '_current_session.csv')
        if not os.path.exists(temp_path):
            temp_path = os.path.join(DATA_DIR, 'kc_house_data.csv')
        
        df = pd.read_csv(temp_path)
        
        target_col = data.get('target_col', '')
        if not target_col or target_col not in df.columns:
            target_col = df.columns[-1]

        requested_features = data.get('features', [])
        # 防呆 1: 目標變數防呆 (移除重複出現在特徵中的目標欄位，避免資訊外洩 R²=1)
        requested_features = [f for f in requested_features if f != target_col and f in df.columns]

        # 防呆 2: 若特徵清單被使用者全數清空，自動備援所有數值特徵
        if not requested_features:
            requested_features = [c for c in df.select_dtypes(include=[np.number]).columns if c != target_col]

        # 防呆 3: 移除全為常數 (零變異數) 的無效特徵，避免奇異矩陣
        valid_features = [f for f in requested_features if df[f].nunique() > 1]
        if valid_features:
            requested_features = valid_features

        df_clean = df[[target_col] + requested_features].dropna()
        if len(df_clean) < 10:
            return jsonify({'status': 'error', 'message': f'有效數據筆數過少 (僅 {len(df_clean)} 筆)，至少需 10 筆樣本才能進行回歸分析'}), 400

        X = df_clean[requested_features]
        y = df_clean[target_col]

        test_ratio = float(data.get('test_ratio', 0.20))
        test_ratio = max(0.1, min(0.5, test_ratio))
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_ratio, random_state=42
        )

        feature_selection_mode = data.get('selection_mode', 'none')
        selected_features = list(requested_features)
        vif_records = []

        if len(selected_features) > 1:
            scaler_temp = StandardScaler()
            X_train_scaled = scaler_temp.fit_transform(X_train)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                for i, feat in enumerate(selected_features):
                    try:
                        v = variance_inflation_factor(X_train_scaled, i)
                    except Exception:
                        v = 999.0
                    vif_records.append({'feature': feat, 'vif': float(v) if not np.isinf(v) and not np.isnan(v) else 999.0})

        if feature_selection_mode == 'vif' and len(selected_features) > 2:
            vif_thresh = float(data.get('vif_threshold', 10.0))
            cur_feats = list(selected_features)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                while len(cur_feats) > 1:
                    sc = StandardScaler()
                    X_sc = sc.fit_transform(X_train[cur_feats])
                    vifs = [variance_inflation_factor(X_sc, i) for i in range(len(cur_feats))]
                    max_vif = max(vifs)
                    if max_vif > vif_thresh:
                        max_idx = vifs.index(max_vif)
                        cur_feats.pop(max_idx)
                    else:
                        break
            selected_features = cur_feats

        elif feature_selection_mode == 'lasso' and len(selected_features) > 2:
            sc = StandardScaler()
            X_train_sc = sc.fit_transform(X_train)
            lasso_cv = LassoCV(cv=5, random_state=42).fit(X_train_sc, y_train)
            non_zero_feats = [f for f, coef in zip(selected_features, lasso_cv.coef_) if abs(coef) > 1e-4]
            if len(non_zero_feats) >= 1:
                selected_features = non_zero_feats

        elif feature_selection_mode == 'kbest' and len(selected_features) > 2:
            k = min(len(selected_features), int(data.get('k_best', 10)))
            kbest = SelectKBest(score_func=f_regression, k=k)
            kbest.fit(X_train, y_train)
            selected_features = [f for f, s in zip(selected_features, kbest.get_support()) if s]

        X_train_sel = X_train[selected_features]
        X_test_sel = X_test[selected_features]

        X_train_const = sm.add_constant(X_train_sel, has_constant='add')
        X_test_const = sm.add_constant(X_test_sel, has_constant='add')
        
        ols_model = sm.OLS(y_train, X_train_const).fit()
        lr_sk = LinearRegression().fit(X_train_sel, y_train)
        
        cv_scores = cross_val_score(lr_sk, X_train_sel, y_train, cv=5, scoring='r2')
        cv_r2_mean = float(cv_scores.mean())
        cv_r2_std = float(cv_scores.std())

        y_test_pred = lr_sk.predict(X_test_sel)

        r2_test = float(lr_sk.score(X_test_sel, y_test))
        r2_train = float(lr_sk.score(X_train_sel, y_train))
        n_test = len(y_test)
        p_features = len(selected_features)
        adj_r2 = float(1 - (1 - r2_test) * (n_test - 1) / (n_test - p_features - 1)) if n_test > p_features + 1 else r2_test
        
        rmse = float(np.sqrt(np.mean((y_test - y_test_pred) ** 2)))
        mae = float(np.mean(np.abs(y_test - y_test_pred)))
        with np.errstate(divide='ignore', invalid='ignore'):
            mape = float(np.nanmean(np.abs((y_test - y_test_pred) / y_test)) * 100)
            if np.isnan(mape) or np.isinf(mape):
                mape = 0.0

        try:
            ridge_bench = RidgeCV(cv=5).fit(X_train_sel, y_train)
            ridge_r2 = float(ridge_bench.score(X_test_sel, y_test))
            ridge_rmse = float(np.sqrt(np.mean((y_test - ridge_bench.predict(X_test_sel)) ** 2)))
        except Exception:
            ridge_r2, ridge_rmse = r2_test, rmse

        try:
            lasso_bench = LassoCV(cv=5, random_state=42).fit(X_train_sel, y_train)
            lasso_r2 = float(lasso_bench.score(X_test_sel, y_test))
            lasso_rmse = float(np.sqrt(np.mean((y_test - lasso_bench.predict(X_test_sel)) ** 2)))
        except Exception:
            lasso_r2, lasso_rmse = r2_test, rmse

        pred_summary = ols_model.get_prediction(X_test_const).summary_frame(alpha=0.05)
        
        eval_df = pd.DataFrame({
            'y_true': y_test.values,
            'y_pred': pred_summary['mean'].values,
            'ci_lower': pred_summary['mean_ci_lower'].values,
            'ci_upper': pred_summary['mean_ci_upper'].values,
            'pi_lower': pred_summary['obs_ci_lower'].values,
            'pi_upper': pred_summary['obs_ci_upper'].values,
            'residual': (y_test.values - pred_summary['mean'].values)
        }).sort_values('y_pred').reset_index(drop=True)

        pi_coverage = float(np.mean((eval_df['y_true'] >= eval_df['pi_lower']) & (eval_df['y_true'] <= eval_df['pi_upper'])) * 100)

        sample_step = max(1, len(eval_df) // 120)
        eval_sampled = eval_df.iloc[::sample_step].to_dict(orient='records')

        residuals = eval_df['residual'].values
        hist_counts, bin_edges = np.histogram(residuals, bins=25)
        residual_bins = [
            {'bin_center': float((bin_edges[i] + bin_edges[i+1])/2), 'count': int(hist_counts[i])}
            for i in range(len(hist_counts))
        ]

        coef_table = []
        conf_int = ols_model.conf_int(alpha=0.05)
        for param_name in ols_model.params.index:
            coef = float(ols_model.params[param_name])
            std_err = float(ols_model.bse[param_name])
            t_val = float(ols_model.tvalues[param_name])
            p_val = float(ols_model.pvalues[param_name])
            ci_l = float(conf_int.loc[param_name, 0])
            ci_u = float(conf_int.loc[param_name, 1])
            coef_table.append({
                'feature': param_name,
                'coef': coef,
                'std_err': std_err,
                't_stat': t_val,
                'p_value': p_val,
                'ci_lower': ci_l,
                'ci_upper': ci_u
            })

        vif_after = []
        if len(selected_features) > 1:
            sc_aft = StandardScaler()
            X_aft_sc = sc_aft.fit_transform(X_train[selected_features])
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                for i, f in enumerate(selected_features):
                    try:
                        v = float(variance_inflation_factor(X_aft_sc, i))
                    except Exception:
                        v = 999.0
                    vif_after.append({'feature': f, 'vif': v if not np.isinf(v) and not np.isnan(v) else 999.0})

        global CURRENT_MODEL
        CURRENT_MODEL = {
            'stats_model': ols_model,
            'sklearn_model': lr_sk,
            'selected_features': selected_features,
            'target_col': target_col,
            'train_means': X_train[selected_features].mean().to_dict(),
            'train_mins': X_train[selected_features].min().to_dict(),
            'train_maxs': X_train[selected_features].max().to_dict()
        }

        return jsonify({
            'status': 'success',
            'metrics': {
                'r2_test': r2_test,
                'r2_train': r2_train,
                'adj_r2': adj_r2,
                'rmse': rmse,
                'mae': mae,
                'mape': mape,
                'cv_r2_mean': cv_r2_mean,
                'cv_r2_std': cv_r2_std,
                'pi_coverage': pi_coverage,
                'train_size': len(X_train),
                'test_size': len(X_test),
                'features_count': len(selected_features),
                'benchmarks': {
                    'ridge_r2': ridge_r2,
                    'ridge_rmse': ridge_rmse,
                    'lasso_r2': lasso_r2,
                    'lasso_rmse': lasso_rmse
                }
            },
            'selected_features': selected_features,
            'vif_table': vif_after,
            'coef_table': coef_table,
            'prediction_samples': eval_sampled,
            'residual_histogram': residual_bins,
            'feature_stats': {
                'means': CURRENT_MODEL['train_means'],
                'mins': CURRENT_MODEL['train_mins'],
                'maxs': CURRENT_MODEL['train_maxs']
            }
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/predict', methods=['POST'])
def api_predict():
    """執行單筆房屋/樣本即時推論 (Deployment 即時預測服務，具備完整防呆與邊界極端值檢查)"""
    try:
        global CURRENT_MODEL
        if CURRENT_MODEL['stats_model'] is None:
            return jsonify({'status': 'error', 'message': '【防呆提示】模型尚未訓練，請先點擊「開始訓練回歸模型」'}), 400
        
        data = request.get_json() or {}
        inputs = data.get('inputs', {})
        
        feats = CURRENT_MODEL['selected_features']
        input_row = {}
        sanitized_warnings = []

        for f in feats:
            raw_val = inputs.get(f)
            # 防呆 1: 處理未填寫、空字串或 None
            if raw_val is None or str(raw_val).strip() == '':
                default_mean = float(CURRENT_MODEL['train_means'].get(f, 0.0))
                input_row[f] = default_mean
                sanitized_warnings.append(f"特徵「{f}」未輸入數值，防呆機制已自動補入訓練平均值 {default_mean:.2f}")
                continue

            # 防呆 2: 處理文字輸入、NaN 或 Inf
            try:
                val = float(raw_val)
                if np.isnan(val) or np.isinf(val):
                    default_mean = float(CURRENT_MODEL['train_means'].get(f, 0.0))
                    input_row[f] = default_mean
                    sanitized_warnings.append(f"特徵「{f}」為非法數值 (NaN/Inf)，已自動替換為平均值 {default_mean:.2f}")
                else:
                    input_row[f] = val
            except (ValueError, TypeError):
                default_mean = float(CURRENT_MODEL['train_means'].get(f, 0.0))
                input_row[f] = default_mean
                sanitized_warnings.append(f"特徵「{f}」輸入「{raw_val}」非有效數字，已自動替換為平均值 {default_mean:.2f}")

            # 防呆 3: 極端外插值預警 (輸入值若超出訓練資料最大值 3 倍或最小值小於 0 針對實體計數特徵)
            train_min = float(CURRENT_MODEL['train_mins'].get(f, 0.0))
            train_max = float(CURRENT_MODEL['train_maxs'].get(f, 100.0))
            cur_val = input_row[f]
            if cur_val < 0 and train_min >= 0:
                sanitized_warnings.append(f"特徵「{f}」輸入負值 ({cur_val})，實務上物理特徵通常大於等於 0，請留意外插誤差！")
            elif cur_val > train_max * 2.5:
                sanitized_warnings.append(f"特徵「{f}」數值 ({cur_val}) 大幅超越訓練集最大值 ({train_max:.1f})，屬極端外插預測！")

        df_input = pd.DataFrame([input_row])
        df_input_const = sm.add_constant(df_input, has_constant='add')
        
        if 'const' not in df_input_const.columns:
            df_input_const.insert(0, 'const', 1.0)
            
        pred_res = CURRENT_MODEL['stats_model'].get_prediction(df_input_const).summary_frame(alpha=0.05)
        
        y_pred = float(pred_res['mean'].iloc[0])
        ci_lower = float(pred_res['mean_ci_lower'].iloc[0])
        ci_upper = float(pred_res['mean_ci_upper'].iloc[0])
        pi_lower = float(pred_res['obs_ci_lower'].iloc[0])
        pi_upper = float(pred_res['obs_ci_upper'].iloc[0])

        return jsonify({
            'status': 'success',
            'prediction': y_pred,
            'confidence_interval_95': {'lower': ci_lower, 'upper': ci_upper},
            'prediction_interval_95': {'lower': pi_lower, 'upper': pi_upper},
            'inputs_used': input_row,
            'warnings': sanitized_warnings
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f"預測計算失敗：{str(e)}"}), 400
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 400


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 70)
    print("  AIoT HW2 - 多元線性回歸互動式 Web 分析平台已啟動！")
    print(f"  請開啟瀏覽器前往：http://127.0.0.1:{port}")
    print("=" * 70)
    app.run(host='0.0.0.0', port=port, debug=False)
