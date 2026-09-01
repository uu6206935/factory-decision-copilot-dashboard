# 1.7.4 Japanese UI + Markdown

- 主要な画面ラベル、状態、データ種別、結合種別、Lineage詳細を日本語化。
- DeepSeekの自動分析回答をMarkdownとして安全に描画。
- 見出し、太字、箇条書き、番号リスト、表、コード、引用に対応。
- Markdown HTMLはMistuneで生成し、Bleachの許可リストでサニタイズ。
- DeepSeekの最終回答プロンプトを「日本語Markdown」固定へ強化。
- ポートを8174に分離し、1.7.3との混在を防止。
