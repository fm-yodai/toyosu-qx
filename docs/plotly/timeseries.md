# Plotly 時系列ガイド

Plotlyは時系列データ向けにレンジスライダー、レンジセレクタ、欠損区間（`rangebreaks`）などの機能を標準提供しています。公式リファレンス: https://plotly.com/python/time-series/

## 基本: Plotly Express

```python
import plotly.express as px
import pandas as pd

df = pd.read_parquet("data/runs/2025-11-11_084402Z/kpi.parquet")
system = df[df["metric"] == "system_utilization"]

fig = px.line(
    system,
    x="ts",
    y="value",
    title="System utilization",
    markers=True
)
fig.update_layout(template="plotly_white", hovermode="x unified")
fig.show()
```

## レンジスライダーとセレクター

Plotly公式`time-series.md`にもあるとおり、X軸に`rangeslider`を付与することで長時間データを操作できます。

```python
fig.update_xaxes(
    rangeselector=dict(
        buttons=[
            dict(count=1, label="1h", step="hour", stepmode="backward"),
            dict(count=6, label="6h", step="hour", stepmode="backward"),
            dict(step="all")
        ]
    ),
    rangeslider=dict(visible=True)
)
```

## KPIダッシュボード（Graph Objects + サブプロット）

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def build_timeseries(run_id: str) -> go.Figure:
    kpi = pd.read_parquet(f"data/runs/{run_id}/kpi.parquet")
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("稼働率", "累積距離", "リードタイム", "配送完了数"),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )

    util = kpi[kpi["metric"] == "system_utilization"]
    fig.add_trace(go.Scatter(x=util["ts"], y=util["value"], name="Utilization"), row=1, col=1)

    distance = kpi[kpi["metric"] == "distance_cumulative_m"]
    fig.add_trace(go.Scatter(x=distance["ts"], y=distance["value"], fill="tozeroy", name="Distance"), row=1, col=2)

    lead = kpi[kpi["metric"] == "lead_time_avg_min"]
    fig.add_trace(go.Scatter(x=lead["ts"], y=lead["value"], name="Lead Time"), row=2, col=1)

    deliveries = pd.read_parquet(f"data/runs/{run_id}/events.parquet")
    deliveries = deliveries[deliveries["event"] == "order_delivered"]
    by_hour = deliveries.groupby(deliveries["ts"].dt.floor("H")).size().reset_index(name="count")
    fig.add_trace(go.Bar(x=by_hour["ts"], y=by_hour["count"], name="Deliveries"), row=2, col=2)

    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        height=800,
        title=f"KPI dashboard – {run_id}"
    )
    fig.update_xaxes(rangeslider_visible=True, row=1, col=1)
    return fig
```

## 欠損区間の非表示（Range Breaks）

シミュレーションが1日単位で、夜間はデータが無い場合は`rangebreaks`でギャップを削除できます。

```python
fig.update_xaxes(
    rangebreaks=[
        dict(bounds=["sat", "mon"]),  # 週末をスキップ
        dict(bounds=[0, 6], pattern="hour")  # 深夜0-6時をスキップ
    ]
)
```

## リサンプリングとダウンサンプリング
- `df.resample("5min", on="ts").sum()`で5分粒度に。
- Plotlyコミュニティ公式の`plotly-resampler`（https://github.com/predict-idlab/plotly-resampler）を使うとズームに応じて自動ダウンサンプリング可能。
- 30万点を超える場合は`Scattergl`に切り替える：`go.Scattergl`.

## アノテーションとSLA

```python
fig.add_hline(y=0.85, line_dash="dash", line_color="red", annotation_text="目標稼働率 85%")
fig.add_vrect(x0=start, x1=end, line_width=0, fillcolor="rgba(255,0,0,0.1)", annotation_text="ピーク時間")
```

## marimoとの連携
- `metric = mo.ui.dropdown(...)`で選択したKPIをPlotlyへ渡し、Figureを`mo.ui.plotly(fig)`で返すだけで再描画。
- `mo.ui.table`に最後のNポイントを表示し、Plotlyのホバーと手元数値を比較できるようにする。

## ベストプラクティス
1. **UTCかローカルかを明記**: `fig.update_xaxes(title="時刻 (JST)")`。
2. **hovertemplate**で複数列を整形：`hovertemplate="時刻=%{x|%H:%M}<br>稼働率=%{y:.1%}<extra></extra>"`。
3. **Y軸範囲**を固定してrun間比較を容易に。
4. **カラーパレット**を`color_discrete_map`で統一。
5. **`fig.write_html(..., include_plotlyjs="cdn")`**で軽量なレポートを生成。

## 参考リンク
- Time series overview: https://plotly.com/python/time-series/
- Range slider/selector: https://plotly.com/python/range-slider/
- Resampler: https://github.com/predict-idlab/plotly-resampler
