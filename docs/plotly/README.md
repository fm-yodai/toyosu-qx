# Plotly ガイド

Plotly.pyはPlotly.jsをバックエンドとするPython向けインタラクティブ可視化ライブラリです。公式ドキュメントは https://plotly.com/python/ に公開されており、30種類以上のチャート、アニメーション、地図、3D表現をブラウザで描画できます。

## インストール

```bash
pip install plotly
# or: pip install "plotly>=5.22" for the latest stable release
```

Plotlyは純粋なPythonライブラリなのでToyosu-QXのuv環境にもそのまま追加できます。Jupyter依存はなく、marimoやCLIスクリプトから直接利用できます。

## 2種類のAPI

| API | 目的 | 典型コード | リンク |
| --- | --- | --- | --- |
| Plotly Express (`plotly.express` or `px`) | 高レベル・宣言的。DataFrameから素早くチャートを生成 | `px.line(df, x="ts", y="value", color="metric")` | [Express入門](https://plotly.com/python/plotly-express/) |
| Graph Objects (`plotly.graph_objects` or `go`) | 低レベル・完全制御。複雑なレイアウトやサブプロットに向く | `fig = go.Figure(); fig.add_trace(go.Scatter(...))` | [Reference](https://plotly.com/python/reference/) |

サブプロットは`plotly.subplots.make_subplots`で行と列を宣言し、`go`トレースを配置します。Toyosu-QXの集計ダッシュボード（稼働率・走行距離など）はExpressで下書き→GraphObjectsで細部を詰める、という流れが効率的です。

## Toyosu-QXでの活用ポイント
- **Phase 1**: `uv run python run.py ...`で生成するHTMLレポートにPlotly図を埋め込み、`fig.write_html("data/runs/<id>/report.html", include_plotlyjs="cdn")`で静的成果物を保存。
- **Phase 2**: marimoノートブック内で`mo.ui.plotly(fig)`としてリアクティブに表示。UI操作（スライダー、ドロップダウン）でPlotly図を再描画できます。
- **再利用性**: 同じFigureを`plotly.io.to_json`でシリアライズし、`generate_report.py`とmarimoの両方で読むことが可能。

## サンプル: KPIダッシュボード骨子

```python
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def build_dashboard(run_id: str) -> go.Figure:
    kpi = pd.read_parquet(f"data/runs/{run_id}/kpi.parquet")
    events = pd.read_parquet(f"data/runs/{run_id}/events.parquet")

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("稼働率", "距離", "リードタイム", "配送件数"),
        specs=[[{"type": "scatter"}, {"type": "scatter"}],
               [{"type": "scatter"}, {"type": "bar"}]]
    )

    util = kpi[kpi["metric"] == "system_utilization"]
    fig.add_trace(
        go.Scatter(x=util["ts"], y=util["value"], name="Utilization"),
        row=1, col=1
    )

    # ...他トレース...

    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        height=800,
        title=f"Toyosu-QX KPI Dashboard<br><sup>{run_id}</sup>"
    )
    fig.update_xaxes(rangeslider_visible=True, row=1, col=1)
    return fig
```

`fig.write_html(..., full_html=True)`で自己完結型HTML、`fig.to_dict()`でJSONを生成できます。

## HTML出力と共有

```python
fig.write_html("data/runs/2025-11-11_084402Z/dashboard.html")
fig.write_image("data/runs/..../kpi.png", scale=2)  # kaleidoが必要
```

- HTMLはPlotly.jsを同梱できるため、ブラウザだけでインタラクティブ。`include_plotlyjs="cdn"`でCDN利用も可能。
- 静的画像化には`pip install -U kaleido`が必要（Plotly公式推奨のヘッドレスエクスポータ）。

## 推奨ユースケース
1. **時系列**: 稼働率やリードタイム。`rangeslider`と`rangeselector`を活用（`doc/python/time-series.md`）。
2. **ヒートマップ**: 時間×エリアの需要や滞留。`px.imshow`や`go.Heatmap`で色スケールを調整。
3. **サンキー図**: 仲卸→小売の流れ。`go.Sankey`でリンク値を重量ベースに。
4. **アニメーション**: ターレの移動、KPIの推移再生。`animation_frame`を時刻に設定。

詳細は各トピック別ファイル（`animations.md`, `heatmaps.md`, `sankey.md`, `timeseries.md`）を参照してください。
