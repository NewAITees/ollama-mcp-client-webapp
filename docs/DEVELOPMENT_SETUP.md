# 開発環境のセットアップ

このドキュメントでは、Ollama MCP Client & Agent の開発環境をセットアップする手順を説明します。

## 前提条件

開発を始める前に、以下のソフトウェアがインストールされていることを確認してください：

- Python 3.11以上
- Poetry（Python依存関係マネージャ）
- Ollama
- Git

```mermaid
graph TD
    A[Python 3.11+] -->|必須| D[開発環境]
    B[Poetry] -->|必須| D
    C[Ollama] -->|必須| D
    E[Git] -->|必須| D
    F[エディタ/IDE] -->|推奨| D
    
    style D fill:#d4f1f9,stroke:#0077b6
```

## 環境セットアップ手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/yourusername/ollama-mcp-client.git
cd ollama-mcp-client
```

### 2. 開発用仮想環境の作成

```bash
# poetryをインストール（まだの場合）
curl -sSL https://install.python-poetry.org | python3 -

# 開発用依存関係を含むすべての依存関係をインストール
poetry install --with dev

# 仮想環境を有効化
poetry shell
```

### 3. Ollamaのセットアップ

Ollamaをまだインストールしていない場合は、[Ollama公式サイト](https://ollama.com/download)からダウンロードしてインストールしてください。

必要なモデルをダウンロード：

```bash
# 基本モデルをプルする
ollama pull llama3
ollama pull mistral
```

### 4. 開発用サーバーのセットアップ

テスト用MCPサーバーをセットアップします：

```bash
# 例：サンプルサーバーをクローン
git clone https://github.com/example/mcp-server-example.git
cd mcp-server-example

# 依存関係をインストール
poetry install
```

### 5. プレコミットフックの設定

コードの品質を保つために、プレコミットフックを設定します：

```bash
# プレコミットをインストール
poetry add --group dev pre-commit

# プレコミットフックを設定
pre-commit install
```

## 開発用フォルダ構成

プロジェクトのフォルダ構成は以下の通りです：

```
ollama-mcp-client/
├── app.py                 # メインアプリケーションエントリーポイント
├── ollama_mcp/            # メインパッケージ
│   ├── __init__.py
│   ├── client.py          # MCPクライアント実装
│   ├── agent.py           # エージェントフレームワーク
│   ├── debug.py           # デバッグユーティリティ
│   ├── tools.py           # ツール定義と実行
│   ├── models.py          # モデル管理
│   └── ui/                # Gradio UI
│       ├── __init__.py
│       ├── app.py
│       ├── components.py
│       └── pages/
├── examples/              # 使用例
├── tests/                 # テストコード
├── docs/                  # ドキュメント
├── .pre-commit-config.yaml # プレコミット設定
├── pyproject.toml         # プロジェクト設定
└── poetry.lock          # 依存関係のロックファイル
```

## 開発ワークフロー

### 1. 機能実装

1. 新しいブランチを作成：
   ```bash
   git checkout -b feature/new-feature-name
   ```

2. コードを実装し、テストを追加

3. フォーマットとリンターを実行：
   ```bash
   # コードフォーマット
   poetry run format
   
   # インポート順序の整理
   poetry run lint
   
   # 型チェック
   poetry run typecheck
   ```

4. テストを実行：
   ```bash
   # 全テスト実行
   poetry run test
   
   # カバレッジ付きでテスト実行
   poetry run pytest --cov=ollama_mcp
   ```

### 2. アプリケーションの実行

開発中にアプリケーションを実行するには：

```bash
# メインアプリケーションを実行
poetry run app

# または特定の例を実行
poetry run python examples/basic_client.py
```

## デバッグ

### VSCode でのデバッグ

VSCode を使用している場合は、次の `.vscode/launch.json` 設定を使用できます：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Run App",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/app.py",
            "console": "integratedTerminal",
            "justMyCode": false,
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        },
        {
            "name": "Run Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": false,
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
```

### トラブルシューティング

よくある問題と解決策：

```mermaid
flowchart TD
    A[問題が発生] --> B{Ollamaが実行中?}
    B -->|いいえ| C[Ollamaを起動する]
    B -->|はい| D{MCPサーバーが実行中?}
    D -->|いいえ| E[MCPサーバーを起動する]
    D -->|はい| F{環境変数が設定済み?}
    F -->|いいえ| G[.env ファイルを確認する]
    F -->|はい| H{依存関係の問題?}
    H -->|はい| I[依存関係を再インストールする]
    H -->|いいえ| J{ログで詳細を確認}
    
    C --> K[再テスト]
    E --> K
    G --> K
    I --> K
    J --> L[Issueを開く]
    
    style A fill:#ffcdd2,stroke:#c62828
    style K fill:#c8e6c9,stroke:#2e7d32
    style L fill:#bbdefb,stroke:#1976d2
```

#### Ollamaの問題

**症状**: `Failed to connect to Ollama server` エラーが発生する

**解決策**:
1. Ollamaが実行中か確認：
   ```bash
   # プロセスを確認
   ps aux | grep ollama
   
   # 必要に応じて起動
   ollama serve
   ```

2. Ollamaの動作を確認：
   ```bash
   # 簡単なモデル呼び出しでテスト
   ollama run llama3 "hello"
   ```

#### MCPサーバーの問題

**症状**: `Connection refused` または `MCP server not responding` エラーが発生する

**解決策**:
1. サーバーが実行中か確認
2. サーバーのパスが正しいか確認
3. サーバーのログでエラーを確認

#### 依存関係の問題

**症状**: `ImportError` または `ModuleNotFoundError` が発生する

**解決策**:
```bash
# 仮想環境が有効化されているか確認
# 依存関係を再インストール
poetry install
```

## 貢献の開始

これで開発環境のセットアップが完了しました。貢献を始める前に[CONTRIBUTING.md](CONTRIBUTING.md)を確認し、プロジェクトのコード規約とワークフローを理解してください。

質問がある場合は、Issueトラッカーで質問するか、メインリポジトリのDiscussionsセクションを利用してください。