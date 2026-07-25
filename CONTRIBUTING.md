# コントリビューション

> 本リポジトリは個人プロジェクトの公開実装です。
> 利用方法・必須前提・クイックスタートは [README.md](README.md) を参照してください。

## Pull Request について

**Pull Request は基本的に受け付けていません。** 制作運用 (新エピソードの企画・制作) に集中するため、外部からのコード変更をマージする余裕がない方針です。

[MIT License](LICENSE) で配布しているので、自由に Fork して使ってください。Fork 先で改造・転用・別プロジェクトへの組み込みは歓迎します。

## バグ報告

GitHub Issue でバグ報告を受け付けています。Issue Template ([.github/ISSUE_TEMPLATE/bug_report.md](.github/ISSUE_TEMPLATE/bug_report.md)) を利用してください。

報告された Issue は確認しますが、修正対応のタイミングは制作運用に依存するため保証はありません。重要度の高いバグ (動画生成が完全に止まる等) は優先対応する想定ですが、軽微な問題は将来の余裕枠で対応する場合があります。

## Fork 後の運用にあたって

Fork して自前で運用する場合の参考情報:

- 環境構築は [README.md](README.md) のクイックスタートを参照
- パイプライン前の静的健全性検査: `python scripts/smoke_test.py` (数秒)
- lint チェック: `python -m ruff check src/ scripts/`
- 詳細な仕様・規約は `docs/` 配下を参照 ([docs/INDEX.md](docs/INDEX.md) が入口)

## ライセンス

本プロジェクトのコードは [MIT License](LICENSE) で配布されています。
