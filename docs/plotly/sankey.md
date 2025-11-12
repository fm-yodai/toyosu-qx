# Plotly サンキー図 ガイド

Plotlyの`go.Sankey`トレースはフロー量を幅で表す図を描画します。エネルギーフローの公式サンプルなどが https://plotly.com/python/sankey-diagram/ にまとまっています。

## 基本構造

```python
import plotly.graph_objects as go

fig = go.Figure(data=[go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=["Source A", "Source B", "Dest 1", "Dest 2"]
    ),
    link=dict(
        source=[0, 0, 1],
        target=[2, 3, 2],
        value=[8, 4, 2]
    )
)])
fig.update_layout(title_text="Basic Sankey Diagram", font_size=12)
fig.show()
```

- `source`/`target`はノード配列のインデックス。
- `value`は流量。Toyosuでは`load_kg`や`order_count`が候補。
- `arrangement="snap"`を設定するとノード位置を自動調整します。

## Toyosu-QXユースケース

```python
import pandas as pd
import plotly.graph_objects as go

deliveries = (
    pd.read_parquet(f"data/runs/{run_id}/events.parquet")
      .query("event == 'order_delivered'")
      .groupby(["wholesaler", "retailer"])["load_kg"].sum()
      .reset_index()
)

wholesalers = deliveries["wholesaler"].unique().tolist()
retailers = deliveries["retailer"].unique().tolist()
nodes = wholesalers + retailers

deliveries["source_idx"] = deliveries["wholesaler"].map(nodes.index)
deliveries["target_idx"] = deliveries["retailer"].map(nodes.index)

fig = go.Figure(data=[go.Sankey(
    node=dict(
        label=nodes,
        color=["#1f77b4"] * len(wholesalers) + ["#ff7f0e"] * len(retailers),
        pad=20,
    ),
    link=dict(
        source=deliveries["source_idx"],
        target=deliveries["target_idx"],
        value=deliveries["load_kg"],
        hovertemplate="仲卸 %{source.label} → 小売 %{target.label}<br>%{value:.0f} kg<extra></extra>"
    )
)])
fig.update_layout(title=f"Flow of goods – {run_id}", font_size=11)
```

### 発展: ハブを挿入
仲卸→ハブ→小売の2段階にしたい場合は、ノードリストへハブを追加し、`source/target`を2セット追加します。Plotly 5.19+では`link.hovercolor`でリンクごとにホバー色を指定できます。

## ノード・リンクの追加属性
- `node.customdata` + `node.hovertemplate`: ノードに補足情報を表示（例: 平均距離）。
- `link.color`: 1対1で色を指定。`"rgba(r,g,b,0.5)"`で透明度設定。
- `link.label`: 凡例テキストを設定（Plotly公式`hovertemplate`例参照）。
- `valueformat="/.1f"`や`valuesuffix=" kg"`で単位を固定。

## 実務チェックリスト
1. **ノード順序を固定**: `nodes`リストをドメイン共通順で作成し、run間比較でも位置が変わらないようにする。
2. **流量の正規化**: 非常に小さいリンクは丸める（例: 1kg未満はまとめる）と視認性が上がる。
3. **ホバー情報**: `hovertemplate`にrun_idや注文数も含めるとレビューしやすい。
4. **アクセシビリティ**: 色だけに頼らず、`link.label`や`node.line`で境界を明示。
5. **marimo統合**: `mo.ui.plotly(fig)`に渡すだけでドラッグ移動やホバーが保持される。

## 参考リンク
- Plotly公式チュートリアル: https://plotly.com/python/sankey-diagram/
- サンプルJSON（エネルギーフロー）: `https://raw.githubusercontent.com/plotly/plotly.js/master/test/image/mocks/sankey_energy.json`
