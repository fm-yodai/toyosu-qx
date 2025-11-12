# marimo ガイド

marimoはPython 3.12+で動作する**リアクティブ型ノートブック兼アプリフレームワーク**です。すべてのセルは依存グラフで管理され、値の変更が即座に下流へ伝播します（`docs/guides/reactivity.md`）。Toyosu-QXではPhase 2以降のインタラクティブ分析環境として採用し、`data/runs/<run_id>/`配下のParquetログを再計算・再可視化する用途に位置づけます。

## なぜmarimoか
- **再現性とGit適性**: ノートブックは通常の`.py`ファイルとして保存され、`marimo.App()`と`@app.cell`でセルを宣言します。JSON差分を扱う必要がなく、CIでpytestやmypyをそのまま走らせられます（`docs/guides/testing/pytest.md`）。
- **リアクティブ実行**: 依存セルだけが再実行されるため、重いKPI算出も必要な時だけ動きます。循環依存は実行時に検出されます（`docs/guides/reactivity.md`）。
- **UIとSQLの標準サポート**: `mo.ui.slider`や`mo.ui.table`などのウィジェットに加えて、DuckDBを用いたSQLセルでParquet/S3/HTTPのデータを直接参照できます（`docs/guides/working_with_data/sql.md`）。
- **アプリ／スクリプト両対応**: `marimo run notebook.py`でWebアプリ提供、`python notebook.py --foo 1`で非対話的スクリプトとしても利用できます（`docs/api/cli_args.md`）。
- **安全な配布**: `marimo export html`でセルを評価した結果を静的HTMLに変換できます（`docs/guides/exporting.md`）。`--token`オプションで簡易認証も有効化できます（`docs/guides/deploying/authentication.md`）。

## インストールと起動

```bash
# 推奨: SQLセルやAI補助を含むフルセット
pip install "marimo[recommended]"
# 既存uv環境からエディタを開く
uv run --with marimo marimo edit notebooks/analysis_marimo.py

# 公式チュートリアル
marimo tutorial intro
```

Toyosu-QXではuv管理下で開くのが安全です。ローカルパッケージをサンドボックスに差し込みたい場合は`uv add --script notebooks/analysis_marimo.py . --editable`が利用できます（`docs/guides/package_management/notebooks_in_projects.md`）。

## ノートブックの構造

```python
import marimo as mo

app = mo.App()


@app.cell
def _(mo=mo):
    import pandas as pd
    run_id = "2025-11-11_084402Z"
    events = pd.read_parquet(f"data/runs/{run_id}/events.parquet")
    return run_id, events


@app.cell
def _(mo=mo):
    alpha = mo.ui.slider(0.1, 1.0, value=0.3, step=0.05, label="積込係数 α (s/kg)")
    min_load = mo.ui.slider(0.0, 1.0, value=0.5, step=0.1, label="最小積載率")
    return alpha, min_load


@app.cell
def _(events, alpha, min_load, mo=mo):
    filtered = events[events["load_ratio"] >= min_load.value]
    mo.md(f"再計算対象イベント: **{len(filtered)}件**")
    return filtered


@app.cell
def _(filtered, alpha, mo=mo):
    import plotly.express as px

    kpi = recompute_kpis(filtered, alpha=alpha.value)
    fig = px.line(kpi, x="ts", y="utilization", color="metric")
    return mo.ui.plotly(fig)


if __name__ == "__main__":
    app.run()
```

- すべてのセルで依存引数を宣言し、戻り値は次のセルへタプルで渡します。
- UI要素はPythonオブジェクトとして返され、`.value`で最新値を取得します（`tests/_server/ai/snapshots/chat_system_prompts.txt`）。

## Toyosu-QXでのワークフロー
1. `uv run --with marimo marimo edit notebooks/analysis_marimo.py`でエディタを起動。
2. `data/runs/<run_id>/events.parquet`や`kpi.parquet`をセル内で読み込み、`mo.ui`でパラメータを露出。
3. `mo.sql`セルでイベントログやKPIをフィルタし、Plotly/Altair/Matplotlibセルへ渡す。
4. `marimo run ... --host 0.0.0.0 --port 7860`で社内共有用のアプリ化。必要に応じて`--token-password`でアクセス制御。
5. `marimo export html notebooks/analysis_marimo.py -o data/runs/<id>/analysis.html`でレポートを成果物に添付。

## SQL・データ統合メモ
- DuckDB方言のSQLセルでParquet/CSV/S3/HTTPをそのまま参照可能（`SELECT * FROM 'data/runs/2024-.../events.parquet'`）。
- Pythonセルで作成したDataFrameはそのままSQLテーブルとして参照でき、結果セットの変数名は`_result`など自由に指定できます（`tests/_convert/snapshots/sql.md.txt`）。
- `mo.ui.dataframe`でユーザー編集済みデータを`.value`として次セルで利用できます（`docs/guides/working_with_data/dataframes.md`）。

## Plotlyとの連携
`mo.ui.plotly(fig)`にPlotly Figureを渡すだけで再描画とイベントハンドリングが行われます（`docs/guides/working_with_data/plotting.md`）。Toyosu-QXの可視化テンプレートは`docs/marimo/data-visualization.md`を参照。

## 配布と運用
- **アプリとして配信**: `marimo run notebook.py --token --token-password="secret" --host 0.0.0.0`
- **スケジュール実行**: `python notebook.py -- --run-id 2025-11-11_084402Z --alpha 0.3`
- **静的書き出し**: `marimo export html notebook.py -o output.html --watch`

CLI引数は`marimo edit/run ... -- --foo bar`のように`--`以降を`sys.argv`へ受け渡せます（`docs/api/cli_args.md`）。

## 参考リンク
- 公式ドキュメント: https://docs.marimo.io/
- GitHub: https://github.com/marimo-team/marimo
- SQLガイド: https://docs.marimo.io/guides/working_with_data/sql.html
- Exportガイド: https://docs.marimo.io/guides/exporting.html

次に読む: [interactive-ui.md](./interactive-ui.md), [data-visualization.md](./data-visualization.md)
