---
agent: copilot
description: セッション初期化（PROJECT_STATUS.md の読み込みと確認）
alwaysApply: true
---

## ステップ1: VS Code バージョン確認

`.github/vscode-version.txt` を読んでください。

- **`Auto-updated by vscode-version-recorder extension` という行がある場合**: 拡張機能が正常動作中です。そのバージョンを使用してステップ2へ。
- **バージョン番号はあるが上記の行がない場合**: そのバージョンを使用してステップ2へ。その後、以下をユーザーに表示：

  > ⚠️ **ai-context-vscode 拡張機能が検出されませんでした**
  > 自動インストールしますか？

  ユーザーが同意した場合：

  ```powershell
  gh release download v0.2.0 --repo freesemt/ai-context-vscode --pattern "*.vsix" --dir $env:TEMP
  code-insiders --install-extension "$env:TEMP\ai-context-vscode-0.2.0.vsix"
  ```

  インストール後、**VS Code を再起動**するよう案内してください。

- **バージョン番号が未記載またはファイルが存在しない場合**: 以下をユーザーに表示：

  > ⚠️ **VS Code バージョンの記録をお願いします**  
  > メニュー → **ヘルプ** → **バージョン情報** → 最初の行の番号（例: `1.115.0-insider`）を  
  > `.github/vscode-version.txt` の末尾に追記してください。

## ステップ2: alwaysApply 対応チェック

取得したバージョンの数値部分（例: `1.114.0` の `1.114`）が **1.99 以上** かどうか判定してください。

- **1.99 以上** → ✅ `alwaysApply: true` が有効です。自動初期化は正常に動作しています。
- **1.99 未満** → ⚠️ `alwaysApply: true` は動作しません。毎回 `/init` を手動実行してください。

## ステップ3: PROJECT_STATUS.md の要約

`PROJECT_STATUS.md` が存在する場合は読んで、以下を日本語で要約してください：

1. **現在のタスク** — 何に取り組んでいるか
2. **直近の進捗** — 最近完了したこと
3. **次のステップ** — 優先度順に

`PROJECT_STATUS.md` が存在しない場合は「STATUS なし」と記載してください。

最後に「**初期化完了** (リポジトリ名) / VS Code vX.XX.X ✅」と明記してください。

---
Usage: `alwaysApply: true` により新しいチャット開始時に自動実行されます（VS Code 1.99+）。`/init` で手動再実行も可能です。
