# Plotly ヒートマップ ガイド

Plotlyは2種類のアプローチでヒートマップを描画できます。

| パターン | API | 主な用途 | ドキュメント |
| --- | --- | --- | --- |
| `px.imshow` | 格子状データ（行×列）をそのまま表示 | 時間帯×拠点の需要、感度分析結果 | https://plotly.com/python/imshow/ |
| `px.density_heatmap` / `go.Histogram2d` | 点群から2Dヒストグラムを生成 | 位置ログの密度、トラック滞留 | https://plotly.com/python/2d-histogram/ |
| `go.Heatmap` | 低レベル制御。独自カラースケールやアニメーション | KPIマトリクス、差分表示 | https://plotly.com/python/heatmaps/ |

## 基本例（Plotly Express）

```python
import plotly.express as px

df = px.data.medals_wide(indexed=True)
fig = px.imshow(
    df,
    color_continuous_scale="Viridis",
    labels=dict(x="競技", y="国", color="メダル数")
)
fig.update_coloraxes(colorbar_title="Count")
fig.show()
```

## Toyosu-QX: 時間×ゾーンの需要

```python
import pandas as pd
import plotly.express as px

demand = (
    pd.read_parquet(f"data/runs/{run_id}/orders.parquet")
      .assign(hour=lambda df: df["ts"].dt.floor("H"))
      .groupby(["hour", "zone"])
      ["volume_kg"].sum()
      .unstack(fill_value=0)
)

fig = px.imshow(
    demand,
    aspect="auto",
    color_continuous_scale="Inferno",
    origin="lower",
    labels=dict(x="卸売ゾーン", y="時刻", color="需要(kg)")
)
fig.update_layout(
    title=f"Hourly demand heatmap / {run_id}",
    xaxis_side="top"
)
```

## 密度ヒートマップ（2Dヒストグラム）

Plotly公式`2D-Histogram.md`より、点群を自動でビン分けできます。

```python
fig = px.density_heatmap(
    events_df,
    x="x_coord",
    y="y_coord",
    nbinsx=40,
    nbinsy=20,
    color_continuous_scale="Viridis",
    marginal_x="histogram",
    marginal_y="histogram",
    title="ターレ滞留エリア"
)
```

- `histfunc="avg"`を使えば平均滞留時間など任意指標を色に割り当てられます。
- `text_auto=True`でビンの値を表示可能（Plotly 5.5+）。

## Graph Objectsでの細かい調整

```python
import plotly.graph_objects as go

fig = go.Figure(
    data=go.Heatmap(
        z=matrix,
        x=beta_values,
        y=alpha_values,
        colorscale=[[0, "#1f77b4"], [0.5, "#ff7f0e"], [1, "#d62728"]],
        zmin=0,
        zmax=1,
        hovertemplate="α=%{y}<br>β=%{x}<br>稼働率=%{z:.2%}<extra></extra>"
    )
)
fig.update_layout(
    title="感度分析 (α×β)",
    xaxis_title="β (s)",
    yaxis_title="α (s/kg)",
)
```

### カラースケール
- 定義済み: `"Viridis"`, `"Cividis"`, `"IceFire"`など。
- カスタム: `[[0.0, "rgb(...)"], ..., [1.0, "rgb(...)"]]` として`go.Heatmap`へ渡す（Plotly公式`colorscales.md`）。

### 軸・注釈
- `fig.update_xaxes(side="top")`で列ラベルを上部へ。
- `fig.add_annotation`で注釈、`fig.add_shape`で閾値を描画。

## ベストプラクティス
1. **`zmin/zmax`を固定**: 複数run比較で色スケールを揃える。
2. **欠損値は0 or NaNを明示**: `demand.fillna(0)`などで表示を安定させる。
3. **hovertemplateに単位を表示**: `"{z:.1f} kg"`で誤読を防止。
4. **閾値ラインを描く**: `fig.add_hline` `fig.add_vline`でSLA境界を明示。
5. **レスポンス最適化**: 行列が大きい場合は`astype("float32")`やビン数を減らす。

## 参考リンク
- Heatmap basics: https://plotly.com/python/heatmaps/
- 2D histogram/density: https://plotly.com/python/2d-histogram/
- Colorscale cookbook: https://plotly.com/python/colorscales/
