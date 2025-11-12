# 可視化モジュール - 使い方ガイド

## 概要

Toyosu-QXシミュレーションの結果を可視化するためのモジュールです。
PlotlyとMarimoを使用して、インタラクティブなレポートと分析ダッシュボードを提供します。

## 自動レポート生成（Phase 1）

シミュレーション実行後、自動的にHTMLレポートが生成されます。

### シミュレーション実行時に自動生成

```bash
# 通常の実行（レポート自動生成）
python run.py --scenario config/scenario/default.yaml --config config/config.yaml

# レポート生成をスキップ
python run.py --scenario config/scenario/default.yaml --no-report
```

### 既存結果からレポート生成

```bash
# 特定の実行結果からレポートを生成
python generate_report.py 2025-11-11_084402Z --scenario config/scenario/default.yaml
```

## 生成されるレポート

シミュレーション実行後、`data/runs/{run_id}/` に以下のHTMLファイルが生成されます：

| ファイル | 内容 |
|---------|------|
| `report.html` | 全ての可視化を含む統合レポート |
| `dashboard.html` | KPIダッシュボード（稼働率、距離、リードタイムなど） |
| `heatmap_demand.html` | 時間帯別需要ヒートマップ |
| `heatmap_utilization.html` | ターレ稼働状態ヒートマップ |
| `sankey_2layer.html` | 2層配送フロー（仲卸→小売） |
| `sankey_3layer.html` | 3層配送フロー（仲卸→ターレ→小売） |
| `animation_tares.html` | ターレ移動のアニメーション |

## 可視化の種類

### 1. KPIダッシュボード

システム全体のパフォーマンス指標を一覧表示：
- **稼働率推移**: 時間帯ごとのターレ稼働率
- **累積走行距離**: 総移動距離の推移
- **リードタイム分布**: 配送にかかった時間の分布
- **時間帯別配送数**: 時間ごとの配送完了数

```python
from sim.viz import create_kpi_dashboard

fig = create_kpi_dashboard("2025-11-11_084402Z")
fig.show()
```

### 2. 需要ヒートマップ

時間帯×仲卸の需要パターンを可視化：
- 色の濃さで需要量を表現
- ピーク時間帯を特定
- 仲卸ごとの需要パターンを比較

```python
from sim.viz import create_demand_heatmap

fig = create_demand_heatmap("2025-11-11_084402Z", time_bin_sec=3600)  # 1時間単位
fig.show()
```

### 3. ターレ稼働状態ヒートマップ

各ターレの時系列稼働状態を可視化：
- グレー: 待機中（idle）
- オレンジ: 積込中（loading）
- 青: 移動中（traveling）
- 緑: 荷下ろし中（unloading）

```python
from sim.viz import create_tare_utilization_heatmap

fig = create_tare_utilization_heatmap("2025-11-11_084402Z", time_bin_sec=60)  # 1分単位
fig.show()
```

### 4. サンキー図（配送フロー）

配送の流れを矢印で可視化：

**2層フロー（仲卸→小売）**
```python
from sim.viz import create_delivery_sankey

fig = create_delivery_sankey("2025-11-11_084402Z", flow_type="2-layer")
fig.show()
```

**3層フロー（仲卸→ターレ→小売）**
```python
fig = create_delivery_sankey("2025-11-11_084402Z", flow_type="3-layer")
fig.show()
```

### 5. ターレ移動アニメーション

ターレの移動を2Dアニメーションで再生：
- 時間軸でスライダー操作
- ターレごとに色分け
- ホバーで詳細情報表示（ノード、状態、積載量）

```python
from sim.viz import create_tare_animation

# ノード座標を読み込み（シナリオファイルから）
import yaml
with open("config/scenario/default.yaml") as f:
    scenario = yaml.safe_load(f)
node_coords = {n["id"]: (n["x"], n["y"]) for n in scenario["nodes"]}

fig = create_tare_animation("2025-11-11_084402Z", node_coords, time_bin_sec=60)
fig.show()
```

## Pythonスクリプトから使用

### 基本的な使い方

```python
from sim.viz import load_simulation_data, create_kpi_dashboard

# データ読み込み
events_df, kpi_df, metadata = load_simulation_data("2025-11-11_084402Z")

# 可視化作成
fig = create_kpi_dashboard("2025-11-11_084402Z")

# ブラウザで表示
fig.show()

# HTMLファイルとして保存
fig.write_html("my_dashboard.html")

# 静的画像として保存（kaleido が必要）
fig.write_image("my_dashboard.png", width=1400, height=800)
```

### 複数実行の比較

```python
import plotly.graph_objects as go
from sim.viz import load_simulation_data

run_ids = ["2025-11-11_084402Z", "2025-11-11_094532Z"]

fig = go.Figure()

for run_id in run_ids:
    _, kpi_df, _ = load_simulation_data(run_id)
    system_util = kpi_df[kpi_df["metric"] == "system_avg_utilization"]

    fig.add_trace(go.Scatter(
        x=system_util["ts"],
        y=system_util["value"],
        mode="lines",
        name=run_id[:10]
    ))

fig.update_layout(title="稼働率比較", xaxis_title="時刻 (s)", yaxis_title="稼働率")
fig.show()
```

## インタラクティブ分析（Phase 2: Marimo）

Phase 2では、Marimoを使用した対話的分析が可能になります。

### Marimoノートブックの起動

```bash
# 分析ノートブックを起動（Phase 2で実装予定）
marimo edit notebooks/analysis_marimo.py
```

### 主な機能（予定）

- **パラメータ調整**: スライダーで α/β、出発トリガーを変更
- **リアルタイム再計算**: パラメータ変更に応じてKPIを再計算
- **プランナー切り替え**: ルールベース/OR-Tools/量子の比較
- **感度分析**: 複数パラメータの組み合わせを自動探索

## トラブルシューティング

### エラー: ファイルが見つからない

```bash
# run_idを確認
ls -t data/runs/

# 最新の実行結果を使用
python generate_report.py $(ls -t data/runs/ | head -1) --scenario config/scenario/default.yaml
```

### アニメーションが生成されない

アニメーションにはノード座標が必要です。`--scenario` オプションを指定してください：

```bash
python generate_report.py 2025-11-11_084402Z --scenario config/scenario/default.yaml
```

### レポート生成が遅い

大規模シミュレーションの場合、レポート生成に時間がかかることがあります：
- `--no-report` オプションでスキップし、後で生成
- `time_bin_sec` パラメータを大きくして粒度を下げる

## カスタマイズ

### 色やレイアウトの変更

```python
from sim.viz import create_kpi_dashboard

fig = create_kpi_dashboard("2025-11-11_084402Z")

# テーマ変更
fig.update_layout(template="plotly_dark")

# サイズ変更
fig.update_layout(width=1600, height=900)

# タイトル変更
fig.update_layout(title="カスタムダッシュボード")

fig.show()
```

### 独自の可視化を追加

```python
import plotly.express as px
from sim.viz import load_simulation_data

events_df, kpi_df, metadata = load_simulation_data("2025-11-11_084402Z")

# 独自の集計
custom_data = events_df[events_df["event"] == "order_delivered"]
custom_data["hour"] = (custom_data["ts"] / 3600).astype(int)

# カスタムグラフ
fig = px.histogram(custom_data, x="hour", title="配送完了数（時間別）")
fig.show()
```

## 参考リソース

- [Plotly使い方ガイド](./plotly/README.md)
  - [アニメーション](./plotly/animations.md)
  - [サンキー図](./plotly/sankey.md)
  - [ヒートマップ](./plotly/heatmaps.md)
  - [時系列グラフ](./plotly/timeseries.md)
- [Marimo使い方ガイド](./marimo/README.md)（Phase 2）
  - [インタラクティブUI](./marimo/interactive-ui.md)
  - [データ可視化統合](./marimo/data-visualization.md)

## 次のステップ

1. **基本的な可視化**: シミュレーションを実行し、生成されたレポートを確認
2. **パラメータ調整**: config.yamlを変更して複数回実行し、結果を比較
3. **カスタム分析**: Pythonスクリプトで独自の可視化を作成
4. **Phase 2**: Marimoノートブックで対話的分析（実装予定）
