# MCP テストハーネス

MCPサーバーのテストと検証を簡単に行うためのGradioベースのウェブアプリケーションです。Model Context Protocol (MCP) サーバーの機能を直接テストし、結果を詳細にログに記録することができます。

## 特徴

- **複数サーバー対応**: JSON設定ファイルから複数のMCPサーバーを設定可能
- **直感的なUI**: Gradioによる使いやすいウェブインターフェース
- **ツール検証**: 各サーバーのツール一覧の表示、スキーマの確認、実行が可能
- **詳細なログ**: すべてのリクエストとレスポンスを構造化してログに記録
- **TDD設計**: テスト駆動開発に基づいた堅牢な実装

## インストール

### 前提条件
- Python 3.11以上
- Poetry（パッケージ管理ツール）

### セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/yourusername/mcp-test-harness.git
cd mcp-test-harness

# 依存関係のインストール
poetry install
```

## 設定

`config/servers.json` ファイルでMCPサーバーを設定してください。

```json
{
  "mcpServers": {
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": ""
      }
    },
    "sqlite": {
      "command": "uvx",
      "args": ["mcp-server-sqlite", "--db-path", "test.db"]
    }
  }
}
```

環境変数はデフォルトでシステムから取得されますが、必要に応じてファイル内で設定することもできます。

## 使用方法

### アプリケーションの起動

```bash
# Poetryを使用
poetry run python -m mcp_test_harness.app

# または
cd mcp-test-harness
poetry shell
python -m mcp_test_harness.app
```

アプリケーションはデフォルトで http://localhost:7860 で起動します。

### テストの実行

```bash
poetry run pytest
```

## 使い方ガイド

1. **サーバーの選択**: ドロップダウンから接続するMCPサーバーを選択します
2. **ツールの選択**: 利用可能なツール一覧から実行したいツールを選択します
3. **スキーマの確認**: ツールの入力スキーマが自動的に表示されます
4. **引数の入力**: JSONエディタに適切な引数を入力します
5. **ツールの実行**: 「ツールを実行」ボタンをクリックして結果を確認します
6. **ログの確認**: 「ログ」アコーディオンを展開してリクエストの詳細を確認できます

## ログ

すべてのリクエストとレスポンスは `logs/` ディレクトリに詳細なログとして保存されます。ログは人間可読形式とJSON形式の両方で保存され、後から分析できます。

## 開発

このプロジェクトはテスト駆動開発（TDD）の原則に従って実装されています。新機能を追加する場合は、まずテストコードを書いてから実装を行うことをお勧めします。

### プロジェクト構造

```
mcp-test-harness/
├── pyproject.toml        # Poetry設定ファイル
├── mcp_test_harness/     # メインパッケージ
│   ├── __init__.py
│   ├── mcp_client.py     # MCPクライアント
│   ├── config.py         # 設定管理
│   ├── logger.py         # ログ機能
│   └── app.py            # Gradioアプリ
├── config/               # 設定ファイル
│   └── servers.json
├── logs/                 # ログファイル（自動生成）
└── tests/                # テストコード
    ├── __init__.py
    ├── test_config.py
    ├── test_mcp_client.py
    └── test_app.py
```

## トラブルシューティング

- **MCP サーバーが起動しない**: 設定ファイルのコマンドとパスが正しいか確認してください
- **APIキーの問題**: 環境変数が正しく設定されているか確認してください
- **接続エラー**: MCPサーバーが実行可能で、指定されたパラメータで起動できるか確認してください

詳細なエラーメッセージは `logs/` ディレクトリにあるログファイルを参照してください。

## ライセンス

MIT

## 貢献

バグ報告、機能リクエスト、プルリクエストを歓迎します。貢献する前に、テスト駆動開発の原則に従ってください。

---

このツールはMCPサーバーのテストと検証を簡素化し、サーバーの機能を直接確認できるようにするために開発されました。MCPクライアントの開発や、既存MCPサーバーの動作確認に役立ちます。