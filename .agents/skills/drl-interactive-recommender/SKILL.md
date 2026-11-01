---
name: drl-interactive-recommender
description: >-
  Designing interactive Deep Reinforcement Learning (DRL) recommender systems with live human-in-the-loop feedback.
  Includes MDP formulation for user preferences (state embedding with exponential decay), action space candidate masking
  for large item catalogs, real-time single-step PyTorch DQN policy updates, and cold-start exploration management.
  Use this skill when developing AI recommendation engines, dynamic personalized feeds, or interactive DRL web services.
---

# 互動式深度強化學習推薦系統架構 (DRL Interactive Recommender System)

本技能提煉自基於 PyTorch 與 Flask 的互動式電影推薦大專案，涵蓋將使用者即時回饋轉化為**馬可夫決策過程（MDP）**、**大維度動作空間遮罩（Action Masking）**與**線上即時模型微調（Online Continual Adaptation）**的完整架構。

---

## 🧭 1. 推薦系統的 MDP 形式化建模 (MDP Formulation)

傳統協同過濾（Collaborative Filtering）難以捕捉使用者**偏好的即時飄移**與探索冷門偏好。DRL 將推薦過程視為與使用者的連續對話：

```
使用者當前狀態 S_t ──► DQN 推薦代理人 ──► 推薦動作 A_t (Top-K 電影)
        ▲                                            │
        │                                            ▼
   狀態向量更新 ◄────── 使用者即時反饋 R_t ◄───── 使用者瀏覽/點擊/按讚
```

1. **狀態向量 $\mathbf{s}_t \in \mathbb{R}^D$**：
   - 包含維度：類型偏好（Genres） + 導演偏好（Directors） + 演員偏好（Actors）。
   - **時間衰減機制（Exponential Temporal Decay）**：
     $$\mathbf{s}_{t+1} = \lambda \mathbf{s}_t + (1 - \lambda) \mathbf{v}_{\text{item}}, \quad \lambda \in [0.7, 0.95]$$
     讓近期互動的權重高於舊紀錄，動態反應當下興致。
2. **動作空間 $\mathcal{A}$**：
   - 項目資料庫中的候選項目清單（如數千部候選影片）。
3. **獎勵函數 $R_t$**：
   - 喜歡（Like）：$+1.0$
   - 不喜歡 / 略過（Dislike / Skip）：$-0.8$
   - 收藏 / 觀看完成（Watch / Bookmark）：$+2.0$

---

## 🎭 2. 大維度項目候選池與動作遮罩 (Action Masking)

當物品庫龐大且使用者已看過某些影片時，不可直接全域取 $\text{argmax}$，需進行向量化動作遮罩（Masking）：

```python
import torch
import torch.nn as nn
import numpy as np

def get_masked_topk_actions(model: nn.Module, state_vector: np.ndarray, 
                           valid_item_ids: list, total_action_dim: int, k: int = 5,
                           epsilon: float = 0.1) -> list:
    """
    帶有動作遮罩與 ε-greedy 的 Top-K 推薦挑選
    """
    if not valid_item_ids:
        return []
    k = min(k, len(valid_item_ids))

    # ε-greedy 隨機探索
    if np.random.rand() < epsilon:
        import random
        return random.sample(valid_item_ids, k)

    # 深度模型預測各 Action 的 Q 值
    state_tensor = torch.FloatTensor(state_vector).unsqueeze(0)
    with torch.no_grad():
        q_values = model(state_tensor)[0] # 形狀: (total_action_dim,)

    # 遮罩非法或已看過動作 (設定為負無限大)
    mask = torch.full((total_action_dim,), float('-inf'))
    for item_id in valid_item_ids:
        if item_id < total_action_dim:
            mask[item_id] = 0.0

    masked_q = q_values + mask
    top_k_indices = torch.topk(masked_q, k).indices.tolist()
    return top_k_indices
```

---

## ⚡ 3. 線上即時人機互動學習迴圈 (Online Human-in-the-Loop)

與離線批次訓練不同，互動式 DRL 需在使用者點擊按讚或倒讚的當下，即時計算 Loss 並更新神經網路參數：

```python
import torch
import torch.nn as nn
import torch.optim as optim

class OnlineRecommenderAgent:
    def __init__(self, state_dim: int, action_dim: int, lr: float = 0.005, gamma: float = 0.9):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        
        # 輕量三層 MLP，保證即時推論延遲 < 10ms
        self.model = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim)
        )
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()

    def step_learn(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray):
        """單步即時在線學習 (Online Update)"""
        if action >= self.action_dim:
            return

        s_t = torch.FloatTensor(state).unsqueeze(0)
        s_next = torch.FloatTensor(next_state).unsqueeze(0)
        
        # 當前預測 Q 值
        current_q = self.model(s_t)[0, action]

        # 計算 TD 目標值
        with torch.no_grad():
            next_max_q = torch.max(self.model(s_next)[0])
            target_q = reward + self.gamma * next_max_q

        # 單步反向傳播
        loss = self.loss_fn(current_q, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        # 梯度裁切，防止即時激增破壞權重
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
        self.optimizer.step()
```

---

## 🧊 4. 冷啟動與探索策略管理 (Cold-Start & Epsilon Schedule)

新進使用者（或新會話）在尚未表達偏好時，系統應提高隨機探索率，隨後隨著回饋次數平滑降溫：

```python
class ExplorationSchedule:
    def __init__(self, eps_initial: float = 1.0, eps_min: float = 0.05, decay: float = 0.92):
        self.eps = eps_initial
        self.eps_min = eps_min
        self.decay = decay
        self.interaction_count = 0

    def step(self) -> float:
        self.interaction_count += 1
        self.eps = max(self.eps_min, self.eps * self.decay)
        return self.eps
```

---

## 🌐 5. Web 整合實踐 (Flask / FastAPI 路由整合)

```python
# API 範例：前端點擊「喜歡」觸發的即時學習
@app.route('/api/feedback', methods=['POST'])
def handle_feedback():
    data = request.json
    user_id = data['userId']
    movie_id = data['movieId']
    is_liked = data['isLiked'] # True or False

    reward = 1.0 if is_liked else -0.8
    old_state = get_user_state(user_id)
    new_state = update_user_state_vector(old_state, movie_id, decay=0.85)

    # 呼叫 DRL 線上更新
    agent.step_learn(old_state, movie_id, reward, new_state)
    save_user_state(user_id, new_state)

    # 取得下一組動態推薦
    next_recommendations = agent.get_masked_actions(new_state, get_unseen_movies(user_id), k=5)
    return jsonify({"success": True, "recommendations": next_recommendations})
```
