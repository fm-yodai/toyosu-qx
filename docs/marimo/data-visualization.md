# marimo × データ可視化

marimoはPlotly・Altair・Matplotlibをセル内でそのまま返すだけで描画できます。`mo.ui.plotly(fig)`などのラッパーは、出力がUIツリーに組み込まれることと、依存セルが自動的に更新されることを保証します（`docs/guides/working_with_data/plotting.md`）。

## 基本レシピ

```python
@app.cell
def _(mo=mo):
    import pandas as pd
    df = pd.read_parquet("data/runs/2025-11-11_084402Z/kpi.parquet")
    return df


@app.cell
def _(df, mo=mo):
    import plotly.express as px

    fig = px.line(df, x="ts", y="value", color="metric", title="KPI推移")
    fig.update_layout(hovermode="x unified")
    return mo.ui.plotly(fig)
```

- Matplotlibの場合は`plt.gca()`や`plt.gcf()`を返します（`docs/_static/CLAUDE.md`）。
- Altairは`mo.ui.altair_chart(chart)`で双方向リンクを維持できます。

## Toyosu-QX ワークフロー
1. `mo.sql`セルでParquetやS3から必要な指標を抽出。
2. `mo.ui.*`でパラメータを受け取りフィルタ条件に挿入。
3. Plotly/Altair/Mplセルで可視化。
4. `mo.vstack`でKPIテーブル（`mo.ui.table(df)`）とグラフを並べ、`marimo export html`で静的レポート化。

## KPIダッシュボード例

```python
@app.cell
def _(mo=mo):
    metric = mo.ui.dropdown(
        options={
            "system_utilization": "システム稼働率",
            "lead_time_p95": "リードタイムP95",
            "distance_m": "走行距離"
        },
        value="system_utilization",
        label="KPI"
    )
    return metric


@app.cell
def _(metric, mo=mo):
    import duckdb, pandas as pd
    query = f"""
        SELECT ts, metric, value
        FROM read_parquet('data/runs/*/kpi.parquet')
        WHERE metric = '{metric.value}'
        ORDER BY ts
    """
    df = duckdb.query(query).to_df()
    return df


@app.cell
def _(df, metric, mo=mo):
    import plotly.express as px

    fig = px.line(df, x="ts", y="value", color="metric")
    fig.update_xaxes(rangeslider_visible=True)  # Plotly公式time-seriesチュートリアルより
    summary = mo.ui.table(df.tail(200))
    return mo.vstack([mo.ui.plotly(fig), summary])
```

## 空間/フロー系ビジュアル
- **Heatmap**: `px.imshow`や`go.Heatmap`を使い、`fig.update_coloraxes(colorbar_title="需要")`で凡例を整理（Plotly公式`heatmaps.md`）。
- **Sankey**: `go.Sankey(node=..., link=...)`を構築し、`hovertemplate`でノード情報を表示（Plotly `sankey-diagram.md`）。
- **2Dアニメーション**: 移動軌跡は`px.scatter(..., animation_frame="ts", animation_group="tare_id")`が最短（Plotly `animations.md`）。

marimo側では`mo.ui.plotly(fig)`に渡すだけで、再生ボタンやホバー動作が保持されます。

## データプルーフのためのSQLセル

```sql
-- KPIを時刻・ターレ別で集約
result = """
SELECT
  tare_id,
  time_bucket('5 minutes', ts) AS bucket,
  AVG(utilization) AS avg_utilization
FROM read_parquet('data/runs/2025-11-11_084402Z/kpi.parquet')
WHERE metric LIKE 'tare_%_utilization'
GROUP BY tare_id, bucket
ORDER BY bucket
"""
```

SQLセルが返すDataFrame（上記では`result`）を次のPlotlyセルにそのまま流用できます（`tests/_convert/snapshots/sql.md.txt`）。

## エクスポート／共有
- `marimo export html notebook.py -o analysis.html`: すべての可視化を静的HTMLに変換。Plotly依存ファイルは自動的にバンドルされます。
- `marimo run notebook.py --host 0.0.0.0 --token`: 社内共有用のダッシュボードに。Plotly図はWebSocket越しにリアクティブ更新されます。

## ベストプラクティス
1. **セル粒度を分ける**: 「データ取得」「整形」「可視化」を分け、どこが再実行されたかを明確に。
2. **Hover情報を明示**: `fig.update_traces(hovertemplate=...)`で単位やrun_idを表示。
3. **UIとグラフをリンク**: `mo.ui.tabs`内にPlotlyを置くと、表示切替でも状態が保持されます。
4. **`mo.ui.table`とセットで**: 数値検証用のRaw行を隣に表示するとレビューしやすい。
5. **大規模データはDuckDBで集約**: Plotlyは数万点までが快適。`LIMIT`やダウンサンプリングをSQLで行う。

## 参考リンク
- Marimo Plottingガイド: https://docs.marimo.io/guides/working_with_data/plotting.html
- Plotly Python公式: https://plotly.com/python/
- 時系列テクニック: https://plotly.com/python/time-series/
- Sankey: https://plotly.com/python/sankey-diagram/
