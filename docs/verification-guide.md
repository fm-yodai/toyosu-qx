# シミュレーション結果の確認ガイド

このガイドでは、Toyosu-QXシミュレーション実行後の結果確認方法をまとめます。

## 1. 出力ファイルの確認

シミュレーション実行後、`data/runs/{run_id}/` ディレクトリに以下のファイルが生成されます：

```bash
data/runs/
└── {run_id}/              # 例: 2025-11-11_084402Z
    ├── events.parquet     # イベントログ（全ての離散イベント）
    ├── kpi.parquet        # KPI集計結果
    └── meta.jsonl         # 実行メタデータ
```

### ファイル一覧の確認

```bash
# 最新の実行結果を確認
ls -lh data/runs/$(ls -t data/runs/ | head -1)/
```

## 2. メタデータの確認

実行の基本情報を確認します：

```bash
# メタデータの表示
cat data/runs/{run_id}/meta.jsonl | python -m json.tool
```

**含まれる情報:**
- `run_id`: 実行ID（タイムスタンプベース）
- `config_hash`: 設定のハッシュ値（再現性確保）
- `started_at` / `ended_at`: 実行開始・終了時刻
- `num_events`: ログされたイベント数
- `num_tares`: ターレ数
- `num_orders`: 生成された注文数

## 3. KPI結果の確認

### 3.1 Pythonで確認

```python
import pandas as pd

# KPIデータの読み込み
run_id = "2025-11-11_084402Z"  # 実際のrun_idに置き換える
kpi_df = pd.read_parquet(f"data/runs/{run_id}/kpi.parquet")

# 全KPIの表示
print(kpi_df)

# システム全体のKPI
system_kpis = kpi_df[kpi_df["metric"].str.startswith("system_")]
print("\n=== System KPIs ===")
print(system_kpis[["metric", "value"]])

# 注文関連のKPI
order_kpis = kpi_df[
    kpi_df["metric"].str.startswith("lead_time") |
    (kpi_df["metric"] == "fulfillment_rate")
]
print("\n=== Order KPIs ===")
print(order_kpis[["metric", "value"]])

# ターレ別のKPI
tare_kpis = kpi_df[kpi_df["metric"].str.contains("tare_")]
print("\n=== Tare KPIs ===")
for tare_id in ["T1-1", "T1-2", "T2-1", "T2-2", "T3-1", "T3-2"]:
    tare_metrics = tare_kpis[tare_kpis["metric"].str.contains(tare_id)]
    if not tare_metrics.empty:
        print(f"\n{tare_id}:")
        for _, row in tare_metrics.iterrows():
            metric_name = row["metric"].replace(f"tare_{tare_id}_", "")
            print(f"  {metric_name}: {row['value']:.2f}")
```

### 3.2 主要KPIの解説

| KPI | 説明 | 望ましい値 |
|-----|------|-----------|
| `system_avg_utilization` | システム全体の平均稼働率 | 高いほど良い（0.6-0.8が理想） |
| `system_total_distance_m` | 総移動距離（メートル） | 低いほど効率的 |
| `system_total_trips` | 総配送回数 | - |
| `lead_time_mean_sec` | 平均リードタイム（秒） | 低いほど良い |
| `lead_time_p95_sec` | 95パーセンタイルリードタイム（秒） | 低いほど良い |
| `fulfillment_rate` | 注文充足率 | 1.0（100%）が理想 |
| `tare_{id}_utilization` | ターレ個別の稼働率 | バランスが取れていることが重要 |
| `tare_{id}_avg_load_kg` | 1回あたりの平均積載量（kg） | 高いほど効率的（最大200kg） |

## 4. イベントログの確認

### 4.1 イベントデータの読み込み

```python
import pandas as pd
import json

# イベントログの読み込み
run_id = "2025-11-11_084402Z"
events_df = pd.read_parquet(f"data/runs/{run_id}/events.parquet")

print(f"Total events: {len(events_df)}")
print("\nEvent types:")
print(events_df["event"].value_counts())

# 最初の10イベントを表示
print("\nFirst 10 events:")
print(events_df.head(10))
```

### 4.2 イベントタイプ別の集計

```python
# イベントタイプごとのカウント
event_counts = events_df["event"].value_counts()
print("Event type distribution:")
for event_type, count in event_counts.items():
    print(f"  {event_type}: {count}")

# ターレごとのイベント数
tare_events = events_df[events_df["tare_id"].notna()]["tare_id"].value_counts()
print("\nEvents per tare:")
print(tare_events)
```

### 4.3 特定ターレの動きを追跡

```python
# ターレT1-1の全イベントを時系列で表示
tare_id = "T1-1"
tare_events = events_df[events_df["tare_id"] == tare_id].sort_values("ts")

print(f"\n=== {tare_id} Event Timeline ===")
for _, event in tare_events.iterrows():
    print(f"[{event['ts']:>8.0f}s] {event['event']:15s} | "
          f"Node: {event['node']:3s} | State: {event['state']:10s} | "
          f"Load: {event['load_kg']:>5.0f}kg")
```

### 4.4 注文のライフサイクル追跡

```python
# 特定の注文を追跡
order_generated = events_df[events_df["event"] == "order_generated"]
if not order_generated.empty:
    # 最初の注文を取得
    first_order = json.loads(order_generated.iloc[0]["payload"])
    order_id = first_order["order_id"]

    print(f"\n=== Order {order_id} Lifecycle ===")

    # この注文に関連する全イベント
    order_events = events_df[
        events_df["payload"].notna() &
        events_df["payload"].str.contains(order_id)
    ].sort_values("ts")

    for _, event in order_events.iterrows():
        print(f"[{event['ts']:>8.0f}s] {event['event']:20s} | Tare: {event['tare_id']}")
```

## 5. データ品質チェック

### 5.1 整合性チェック

```python
import pandas as pd

run_id = "2025-11-11_084402Z"
events_df = pd.read_parquet(f"data/runs/{run_id}/events.parquet")

# 1. 注文数の整合性
orders_generated = len(events_df[events_df["event"] == "order_generated"])
orders_assigned = len(events_df[events_df["event"] == "order_assigned"])
orders_delivered = len(events_df[events_df["event"] == "order_delivered"])

print("=== Order Flow ===")
print(f"Generated:  {orders_generated}")
print(f"Assigned:   {orders_assigned}")
print(f"Delivered:  {orders_delivered}")
print(f"In-transit: {orders_assigned - orders_delivered}")

# 2. ターレの状態遷移チェック
for tare_id in events_df[events_df["tare_id"].notna()]["tare_id"].unique():
    tare_events = events_df[
        (events_df["tare_id"] == tare_id) &
        (events_df["state"].notna())
    ].sort_values("ts")

    # 状態遷移の確認
    states = tare_events["state"].tolist()
    print(f"\n{tare_id} state transitions: {len(states)} changes")

# 3. 時間範囲の確認
print(f"\n=== Simulation Time ===")
print(f"Start: {events_df['ts'].min():.0f}s")
print(f"End:   {events_df['ts'].max():.0f}s")
print(f"Duration: {(events_df['ts'].max() - events_df['ts'].min())/3600:.1f}h")
```

### 5.2 異常値チェック

```python
# 積載量の異常値チェック
load_events = events_df[events_df["load_kg"].notna()]
over_capacity = load_events[load_events["load_kg"] > 200]

if not over_capacity.empty:
    print("⚠️ WARNING: Over-capacity loads detected!")
    print(over_capacity[["ts", "tare_id", "load_kg", "event"]])
else:
    print("✓ All loads within capacity (200kg)")

# 負の値チェック
negative_loads = load_events[load_events["load_kg"] < 0]
if not negative_loads.empty:
    print("⚠️ WARNING: Negative loads detected!")
    print(negative_loads[["ts", "tare_id", "load_kg", "event"]])
else:
    print("✓ No negative loads")
```

## 6. 簡易分析スクリプト

結果を素早く確認するための簡易スクリプト：

```python
# quick_check.py
import pandas as pd
import sys

if len(sys.argv) < 2:
    print("Usage: python quick_check.py <run_id>")
    sys.exit(1)

run_id = sys.argv[1]

# Load data
kpi_df = pd.read_parquet(f"data/runs/{run_id}/kpi.parquet")
events_df = pd.read_parquet(f"data/runs/{run_id}/events.parquet")

print(f"{'='*50}")
print(f"Simulation Results: {run_id}")
print(f"{'='*50}")

# System metrics
print("\n📊 System Performance:")
system = kpi_df[kpi_df["metric"].str.startswith("system_")]
for _, row in system.iterrows():
    metric = row["metric"].replace("system_", "")
    print(f"  {metric:20s}: {row['value']:>10.2f}")

# Order metrics
print("\n📦 Order Metrics:")
orders = kpi_df[
    kpi_df["metric"].str.startswith("lead_time") |
    (kpi_df["metric"] == "fulfillment_rate")
]
for _, row in orders.iterrows():
    if "sec" in row["metric"]:
        print(f"  {row['metric']:20s}: {row['value']:>8.0f}s ({row['value']/60:>6.1f}min)")
    else:
        print(f"  {row['metric']:20s}: {row['value']:>9.1%}")

# Event summary
print("\n📝 Event Summary:")
print(f"  Total events: {len(events_df)}")
event_counts = events_df["event"].value_counts()
for event, count in event_counts.items():
    print(f"    {event:20s}: {count:>6d}")

print(f"\n{'='*50}")
```

使用方法：

```bash
python quick_check.py 2025-11-11_084402Z
```

## 7. 次のステップ

結果確認後、以下のアクションを検討：

1. **パラメータ調整**: config.yamlの値を変更して再実行
   - `min_stay_sec`: 5分ルールの調整
   - `min_load_ratio`: 出発トリガーの閾値
   - `speed_kmph`: 移動速度

2. **シナリオ変更**: scenario/default.yamlを編集
   - ターレ数の増減
   - 需要パターンの変更
   - 配送先の配置変更

3. **複数実行の比較**: 異なる設定で複数回実行し、KPIを比較

4. **可視化の追加** (Phase 2): Plotlyでグラフ生成、marimoで対話的分析

## 8. トラブルシューティング

### エラー: ファイルが見つからない

```bash
# run_idを確認
ls -t data/runs/
```

### KPIが0または異常値

- イベントログを確認して、シミュレーションが正常に実行されたか確認
- `events.parquet`のサイズが0でないか確認

### 充足率が低い

- シミュレーション時間が短すぎる可能性（sim_duration_secを延長）
- ターレ数が需要に対して不足している可能性
