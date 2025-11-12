# marimo UIハンドブック

marimoのUIウィジェット（`mo.ui.*`）は内部でリアクティブグラフに登録され、`.value`にアクセスするセルだけが自動的に再計算されます（`docs/guides/reactivity.md`）。ここではToyosu-QXで頻出する入力部品とレイアウト手法を整理します。

## 基本原則
- **セルごとにUIを生成**: UIインスタンスはPythonオブジェクトなので、戻り値として次のセルに渡して使います。
- **`.value`だけを下流に共有**: 大半のUIは`.value`を読むたびに依存セルが再実行されます。重い計算を避けたい場合は別セルでキャッシュしましょう。
- **明示的なラベルと範囲**: シミュレーション固有の単位や有効範囲をラベルに埋め込みます。

```python
@app.cell
def _(mo=mo):
    run_id = mo.ui.text(value="2025-11-11_084402Z", label="Run ID")
    alpha = mo.ui.slider(0.1, 1.0, value=0.3, step=0.05, label="積込係数 α (s/kg)")
    return run_id, alpha


@app.cell
def _(run_id, alpha):
    events = load_events(run_id.value)
    return recompute(events, alpha=alpha.value)
```

## 代表的な入力ウィジェット

| パターン | API | 主用途 |
| --- | --- | --- |
| スライダー | `mo.ui.slider(start, stop, value, step, label=...)` | 連続量（α, β, 距離閾値） |
| 数値入力 | `mo.ui.number(start, stop, step, value, label=...)` | ターレ台数など整数設定 |
| ドロップダウン | `mo.ui.dropdown(options, value, label=...)` | プランナー種別や需要シナリオ |
| ラジオボタン | `mo.ui.radio(options=dict(...), value=...)` | 出発トリガーの排他選択 |
| チェックボックス | `mo.ui.checkbox(value: bool, label=...)` | 可視化のON/OFF |
| テキスト／テキストエリア | `mo.ui.text`, `mo.ui.text_area` | `run_id`、SQL断片、JSON |
| 日付ピッカー | `mo.ui.date(value="YYYY-MM-DD")` | シミュレーション開始日 |
| マルチセレクト | `mo.ui.multiselect(options, value=[...])` | 比較対象runの選択 |
| テーブル | `mo.ui.table(df, pagination=True)` | KPI一覧やイベントサンプル |

いずれも`docs/api/inputs/`配下で詳細が公開されています。

### 複数パラメータの束ね方

```python
@app.cell
def _(mo=mo):
    alpha = mo.ui.slider(0.1, 1.0, value=0.25, step=0.05, label="α (s/kg)")
    min_load = mo.ui.slider(0.0, 1.0, value=0.5, step=0.1, label="最小積載率")
    planner = mo.ui.dropdown(
        options={"rule": "ルールベース", "ortools": "OR-Tools"},
        value="rule",
        label="プランナー"
    )
    ui_block = mo.vstack([
        mo.md("### パラメータ"),
        mo.hstack([alpha, min_load]),
        planner,
    ])
    return alpha, min_load, planner, ui_block
```

## レイアウトとコンテナ
- `mo.vstack([...])`: 縦方向のスタック。セクションタイトル＋入力群に最適。
- `mo.hstack([...])`: 横並び。関連スライダーを1行でまとめるとスペースを節約できます。
- `mo.ui.tabs({"基本設定": block1, "高度設定": block2})`: UIブロックをタブに区分。
- `mo.ui.expander(label="詳細", children=[...])`: 詳細設定を折り畳み。
- `mo.grid([...], columns=2)`: β版のグリッドレイアウト。複雑なダッシュボードに。

## データ駆動UI

```python
@app.cell
def _(mo=mo):
    import os

    run_ids = sorted(os.listdir("data/runs"), reverse=True)
    run_selector = mo.ui.dropdown(
        options=run_ids,
        value=run_ids[0] if run_ids else None,
        label="分析対象 run_id"
    )
    date_range = mo.ui.date_range(label="需要集計期間")
    return run_selector, date_range


@app.cell
def _(run_selector, date_range):
    if run_selector.value is None:
        return None
    return load_summary(run_selector.value, window=date_range.value)
```

UIの選択肢や既定値は`config/config.yaml`やシナリオファイルから動的に決めるようにすると、設定の二重管理を避けられます。

## KPI分析ビューの雛形

```python
@app.cell
def _(mo=mo):
    metric = mo.ui.dropdown(
        options=["system_utilization", "lead_time_min", "distance_m"],
        value="system_utilization",
        label="表示するKPI"
    )
    tare_filter = mo.ui.multiselect(
        options=available_tares(),
        value=[],
        label="ターレフィルタ (空は全件)"
    )
    return metric, tare_filter


@app.cell
def _(metric, tare_filter):
    df = load_kpi(metric.value, tare_ids=tare_filter.value)
    fig = build_timeseries(df, metric=metric.value)
    return mo.ui.plotly(fig), mo.ui.table(df.tail(200))
```

PlotlyやAltairなど他の可視化ライブラリに渡す際も、`.value`を使うだけで依存グラフが追跡されます。

## ベストプラクティス
1. **説明責任のあるラベル**: 単位（`(kg)`, `(s)`）や基準値をラベルに入れる。
2. **範囲チェックを前段で**: 異常入力は計算セルではなくUIセルで制限する。
3. **長いテキストは`mo.ui.text_area`**で扱い、SQLやJSONを整形。
4. **重い計算はスロットリング**: 中間結果を`mo.state`やキャッシュ関数で保存し、UI操作ごとに全再計算しない。
5. **依存の見える化**: まとめ用セル（例: `ui_block`）でUIを返し、別セルで`mo.vstack([ui_block, charts])`とする。

## 参考リンク
- UI APIリファレンス: https://docs.marimo.io/api/inputs/
- レイアウトガイド: https://docs.marimo.io/guides/working_with_data/plotting.html
- SQLとUIの連携例: `tests/_convert/snapshots/sql.md.txt`
