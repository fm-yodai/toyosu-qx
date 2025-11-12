# 可視化クイックスタート

## 5分で始める可視化

### 1. シミュレーション実行

```bash
# シミュレーションを実行（自動的にレポート生成）
python run.py --scenario config/scenario/default.yaml --config config/config.yaml
```

実行後、以下のように表示されます：

```
Results saved to: data/runs/2025-11-11_084402Z

=== Generating Visualization Report ===
1. Creating KPI dashboard...
   Saved: data/runs/2025-11-11_084402Z/dashboard.html
2. Creating demand heatmap...
   Saved: data/runs/2025-11-11_084402Z/heatmap_demand.html
...

✓ Report generation complete!
  Main report: data/runs/2025-11-11_084402Z/report.html
```

### 2. レポートを開く

```bash
# 最新のレポートをブラウザで開く
open data/runs/$(ls -t data/runs/ | head -1)/report.html

# または、特定のrun_idを指定
open data/runs/2025-11-11_084402Z/report.html
```

### 3. レポートの見方

#### 統合レポート（report.html）
全ての可視化が1ページにまとまっています。

#### 個別レポート
- `dashboard.html`: KPI推移（稼働率、距離、リードタイム、配送数）
- `heatmap_demand.html`: 時間帯×仲卸の需要パターン
- `heatmap_utilization.html`: ターレの稼働状態
- `sankey_2layer.html`: 仲卸→小売の配送フロー
- `sankey_3layer.html`: 仲卸→ターレ→小売の配送フロー
- `animation_tares.html`: ターレ移動のアニメーション

### 4. インタラクティブ機能

生成されたHTMLレポートでは以下の操作が可能です：

- **ズーム**: マウスホイールまたはドラッグでズーム
- **パン**: ドラッグで表示範囲を移動
- **ホバー**: グラフ上にマウスを置くと詳細情報を表示
- **凡例クリック**: 凡例をクリックで系列の表示/非表示を切り替え
- **アニメーション再生**: 再生ボタンで時系列アニメーションを再生
- **スライダー**: 時間軸スライダーで特定の時刻にジャンプ

### 5. 複数実行の比較

```bash
# パラメータを変えて複数回実行
python run.py --scenario config/scenario/default.yaml --seed 42
python run.py --scenario config/scenario/default.yaml --seed 100
python run.py --scenario config/scenario/default.yaml --seed 200

# 結果を確認
ls -t data/runs/
```

Pythonスクリプトで比較：

```python
from sim.viz import load_simulation_data
import plotly.graph_objects as go

run_ids = ["2025-11-11_084402Z", "2025-11-11_094532Z", "2025-11-11_105621Z"]

fig = go.Figure()
for run_id in run_ids:
    _, kpi_df, _ = load_simulation_data(run_id)
    util = kpi_df[kpi_df["metric"] == "system_avg_utilization"]
    fig.add_trace(go.Scatter(x=util["ts"], y=util["value"], name=run_id[:10]))

fig.update_layout(title="稼働率比較", xaxis_title="時刻 (s)", yaxis_title="稼働率")
fig.show()
```

## トラブルシューティング

### レポート生成がスキップされた場合

シミュレーション実行時に `--no-report` を指定した場合や、エラーで生成がスキップされた場合：

```bash
# 後からレポートを生成
python generate_report.py 2025-11-11_084402Z --scenario config/scenario/default.yaml
```

### アニメーションが空白の場合

ノード座標が取得できていない可能性があります。`--scenario` オプションを指定してください：

```bash
python generate_report.py 2025-11-11_084402Z --scenario config/scenario/default.yaml
```

### HTMLファイルが開けない場合

ブラウザで直接開く：

1. ブラウザを開く（Chrome、Firefox、Safariなど）
2. ファイルメニューから「ファイルを開く」を選択
3. `data/runs/{run_id}/report.html` を選択

## 次のステップ

- [詳細な可視化ガイド](./visualization.md)を読む
- [Plotlyドキュメント](./plotly/README.md)でカスタマイズ方法を学ぶ
- Pythonスクリプトで独自の分析を作成
