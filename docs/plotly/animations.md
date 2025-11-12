# Plotly アニメーション ガイド

Plotlyは`animation_frame`と`animation_group`（Express）または`frames`（Graph Objects）を使って時系列・段階的な可視化を提供します。公式ドキュメント: https://plotly.com/python/animations/

## 基本構造（Plotly Express）

```python
import plotly.express as px

df = px.data.gapminder()
fig = px.scatter(
    df,
    x="gdpPercap",
    y="lifeExp",
    animation_frame="year",
    animation_group="country",
    size="pop",
    color="continent",
    log_x=True,
    range_x=[100, 100000],
    range_y=[25, 90],
    title="Life Expectancy vs GDP (Plotly公式例)"
)
fig.show()
```

- `animation_frame`: フレームを識別する列（Toyosuでは秒/分刻みの`ts`）。
- `animation_group`: フレームを跨いで同一オブジェクトを追跡（`tare_id`など）。
- 軸範囲は固定しておくとフレーム間でスケールがぶれません（公式でも`range_x/range_y`を推奨）。

## Toyosu-QX: ターレ移動アニメーション

```python
import pandas as pd
import plotly.express as px

node_coords = load_node_coordinates()  # {"W1": (0, 0), ...}
positions = (
    pd.read_parquet(f"data/runs/{run_id}/events.parquet")
      .query("event in ['departure', 'arrival']")
      [["ts", "tare_id", "node"]]
      .assign(
          x=lambda df: df["node"].map(lambda n: node_coords.get(n, (0, 0))[0]),
          y=lambda df: df["node"].map(lambda n: node_coords.get(n, (0, 0))[1]),
      )
)

fig = px.scatter(
    positions,
    x="x",
    y="y",
    animation_frame="ts",
    animation_group="tare_id",
    color="tare_id",
    hover_name="tare_id",
    range_x=[-50, 350],
    range_y=[-50, 200],
    title=f"Tare movements – {run_id}"
)
fig.update_traces(marker=dict(size=10, opacity=0.8))
fig.update_layout(transition=dict(duration=0))
```

### ポイント
1. `ts`列は昇順でソートし、必要であれば5〜10秒単位に丸めます。
2. 軸範囲を固定しないと各フレームでオートズームされてしまうため`range_x/range_y`を必ず指定。
3. `animation_group`を設定するとターレIDごとの色が一貫します。
4. 大規模runでは`positions.iloc[::2]`などでダウンサンプル。

## KPIヒートマップの時間推移

Expressはフレームを簡単に扱えますが、`go.Figure`で`frames`を手動構築するとボタン制御やスピードを細かく設定できます（公式`heatmap-animation.md`参照）。

```python
import plotly.graph_objects as go

fig = go.Figure(
    data=[go.Heatmap(z=matrix_list[0], x=x_coords, y=y_coords)],
    frames=[
        go.Frame(data=[go.Heatmap(z=matrix_list[i])], name=str(i))
        for i in range(len(matrix_list))
    ],
)
fig.update_layout(
    updatemenus=[{
        "type": "buttons",
        "buttons": [
            {"label": "Play", "method": "animate",
             "args": [None, {"frame": {"duration": 200, "redraw": True},
                             "transition": {"duration": 0}}]},
            {"label": "Pause", "method": "animate",
             "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}]}
        ]
    }]
)
```

## レポート統合のTips
- `fig.write_html(..., auto_play=False)`で初期状態を停止にできます。
- 複数アニメーションを同一HTMLに載せる場合は、それぞれに固有の`id`を付ける（Plotly 5.17+）。
- marimo内では`mo.ui.plotly(fig)`を返せば再生ボタンやスライダーがそのまま利用可能。

## チェックリスト
- [ ] 軸範囲を固定したか（`range_x`, `range_y`, `zmin/zmax`）。
- [ ] データフレームがフレームごとに十分なポイントを持つか。空フレームは避ける。
- [ ] `hovertemplate`で単位を説明し、`extra`情報を整理。
- [ ] `fig.update_layout(sliders=...)`で任意フレームに直接ジャンプできるようにするとレビューが楽になります。
