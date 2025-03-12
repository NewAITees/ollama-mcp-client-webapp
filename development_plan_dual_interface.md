# MCP Test Harness拡張開発計画: デュアルインターフェース（Web/CLI）対応MCPクライアント

## 1. 概要と目的

MCPテストハーネスをWebインターフェース（Gradio）とCLI（コマンドラインインターフェース）の両方で操作可能なデュアルインターフェースシステムとして再構築する。これにより、GUIを好むユーザーとコマンドラインを好むユーザーの両方のニーズに対応し、自動化スクリプトやCI/CDパイプラインへの組み込みも可能になる。

## 2. 設計方針

### 2.1 アーキテクチャ

1. **コアロジックレイヤー**（共通）
   - MCPサーバー通信モジュール
   - ツール管理モジュール
   - 設定管理モジュール

2. **インターフェースレイヤー**（分離）
   - Webインターフェース（Gradio）
   - コマンドラインインターフェース（Click/Typer）

3. **データフローレイヤー**（共通）
   - 設定読み込み
   - レスポンス処理
   - ログ記録

### 2.2 コンポーネント詳細

#### a. 共通コアモジュール
```python
# mcp_test_harness/core/client.py
class MCPTestClient:
    """MCPサーバーとの通信を担当するコアクライアント"""
    
    def __init__(self, config_path=None):
        self.server_config = {}
        self.server_parameters = {}
        self.tools_store = ThreadSafeToolStore()
        
    async def load_configuration(self, config_path=None):
        """設定を読み込む"""
        # 既存のコードをリファクタリング
        
    async def list_servers(self):
        """利用可能なサーバーの一覧を返す"""
        # 既存のコードをリファクタリング
        
    async def list_tools(self, server_name):
        """サーバーの利用可能なツールを返す"""
        # 既存のコードをリファクタリング
        
    async def get_tool_schema(self, server_name, tool_name):
        """ツールのスキーマを取得"""
        # 既存のコードをリファクタリング
        
    async def call_tool(self, server_name, tool_name, args_json):
        """ツールを呼び出す"""
        # 既存のコードをリファクタリング
```

#### b. CLIモジュール
```python
# mcp_test_harness/cli/commands.py
import typer
import asyncio
import json
from rich.console import Console
from rich.table import Table
from ..core.client import MCPTestClient

app = typer.Typer()
console = Console()

@app.callback()
def callback():
    """MCPテストハーネスのコマンドラインインターフェース"""
    pass

@app.command("list-servers")
def list_servers():
    """利用可能なMCPサーバーを一覧表示"""
    client = MCPTestClient()
    servers = asyncio.run(client.load_configuration_and_list_servers())
    
    table = Table(title="利用可能なMCPサーバー")
    table.add_column("サーバー名")
    
    for server in servers:
        table.add_row(server)
    
    console.print(table)

@app.command("list-tools")
def list_tools(server_name: str = typer.Argument(..., help="MCPサーバー名")):
    """指定したサーバーの利用可能なツールを一覧表示"""
    client = MCPTestClient()
    asyncio.run(client.load_configuration())
    tools = asyncio.run(client.list_tools(server_name))
    
    table = Table(title=f"{server_name}の利用可能なツール")
    table.add_column("ツール名")
    table.add_column("説明")
    
    for tool_name, schema in tools:
        name, description = tool_name.split(" - ", 1)
        table.add_row(name, description)
    
    console.print(table)

@app.command("call-tool")
def call_tool(
    server_name: str = typer.Argument(..., help="MCPサーバー名"),
    tool_name: str = typer.Argument(..., help="ツール名"),
    args_file: typer.FileText = typer.Option(None, "--args-file", "-f", help="引数JSONファイル"),
    args_json: str = typer.Option(None, "--args", "-a", help="引数JSON文字列")
):
    """ツールを呼び出す"""
    if args_file and args_json:
        console.print("[bold red]エラー:[/] --args-fileと--argsは同時に指定できません")
        raise typer.Exit(1)
    
    # 引数の取得
    if args_file:
        args = args_file.read()
    elif args_json:
        args = args_json
    else:
        args = "{}"
    
    client = MCPTestClient()
    asyncio.run(client.load_configuration())
    result = asyncio.run(client.call_tool(server_name, tool_name, args))
    
    console.print(result)
```

#### c. Webインターフェースのリファクタリング
```python
# mcp_test_harness/web/app.py
import gradio as gr
from ..core.client import MCPTestClient

def create_app():
    """Gradioアプリケーションを作成"""
    client = MCPTestClient()
    
    # 非同期処理の初期化
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.load_configuration())
    
    # 以下の部分は既存のGradioインターフェースをリファクタリング
    # クライアントコアを使用するように変更
```

#### d. エントリーポイント
```python
# mcp_test_harness/__main__.py
import os
import sys

if __name__ == "__main__":
    # コマンドライン引数に基づいてモードを判定
    if len(sys.argv) > 1 and sys.argv[1] in ["cli", "web"]:
        mode = sys.argv[1]
        # sys.argvからモード引数を削除
        sys.argv.pop(1)
    else:
        # デフォルトはwebモード
        mode = os.environ.get("MCP_HARNESS_MODE", "web")
    
    if mode == "cli":
        from .cli.commands import app
        app()
    else:
        from .web.app import launch_app
        launch_app()
```

## 3. ディレクトリ構造

```
mcp_test_harness/
├── __init__.py
├── __main__.py              # エントリーポイント
├── core/                    # 共通コアロジック
│   ├── __init__.py
│   ├── client.py            # MCPクライアントコア
│   ├── config.py            # 設定管理
│   └── models.py            # データモデル
├── cli/                     # CLIインターフェース
│   ├── __init__.py
│   ├── commands.py          # CLIコマンド定義
│   └── formatters.py        # 出力フォーマッター
├── web/                     # Webインターフェース
│   ├── __init__.py
│   ├── app.py               # Gradioアプリケーション
│   └── handlers.py          # イベントハンドラー
└── utils/                   # 共通ユーティリティ
    ├── __init__.py
    ├── logger.py            # ロギング
    └── async_utils.py       # 非同期ユーティリティ
```

## 4. 実装ロードマップ

### フェーズ1: コア機能リファクタリング（所要期間: 2週間）
1. 既存コードのコアロジックと表示ロジックの分離（4日）
2. 共通インターフェース設計と実装（3日）
3. クライアントコアクラスの設計と実装（4日）
4. スレッドセーフティとリソース管理の改善（3日）

### フェーズ2: CLIインターフェース実装（所要期間: 1週間）
1. CLIコマンド構造設計（2日）
2. 基本コマンド実装（list-servers, list-tools, call-tool）（3日）
3. 高度なCLI機能（インタラクティブモード、自動補完）（2日）

### フェーズ3: インターフェース統合（所要期間: 1週間）
1. エントリーポイント実装とモード切替（2日）
2. Gradioインターフェースのリファクタリング（3日）
3. 共通設定と環境変数の統合（2日）

### フェーズ4: テストと仕上げ（所要期間: 1週間）
1. 単体テストと統合テスト（3日）
2. ドキュメンテーション（2日）
3. パッケージングとデプロイ（2日）

## 5. 技術要件

- **必須ライブラリ**:
  - typer: ^0.9.0（CLIインターフェース）
  - rich: ^13.7.0（コンソール出力の装飾）
  - pydantic: ^2.6.0（スキーマバリデーション）
  - gradio: ^4.0.0（Webインターフェース）
  
- **開発ツール**:
  - pytest（テスト）
  - black（コードフォーマット）
  - isort（インポート整理）
  - mypy（型チェック）

## 6. 運用と保守

### 6.1 ヘルプシステム
- コマンドラインインターフェースでは、各コマンドの詳細なヘルプを提供
- Webインターフェースでは、ツールチップとヘルプパネルを追加

### 6.2 エラーハンドリング
- CLIとWeb両方で一貫したエラーメッセージを提供
- エラーコードとログレベルの標準化

### 6.3 設定管理
- 共通の設定ファイルを両インターフェースで使用
- 環境変数によるコンフィギュレーションのオーバーライド

## 7. 期待される効果と利点

1. **拡張された使用性**:
   - GUIとCLIの両方でMCPサーバーとの通信が可能に
   - 多様なユーザー層とユースケースに対応

2. **自動化の容易さ**:
   - スクリプトやCIパイプラインからのMCPツール呼び出しが簡単に
   - バッチ処理とスケジュールタスクに活用可能

3. **コードの品質向上**:
   - 関心の分離によるメンテナンス性の向上
   - コア機能の再利用性と拡張性が向上

4. **本番環境への適合性**:
   - サーバーレス環境でのCLI実行
   - ヘッドレス環境での動作が可能

## 8. 将来の拡張可能性

1. **API提供**:
   - RESTful APIとしてのエンドポイント公開

2. **パイプライン機能**:
   - 複数ツール呼び出しを連鎖させるパイプライン定義

3. **プラグインシステム**:
   - サードパーティによる拡張モジュールのサポート

4. **カスタムサーバー定義**:
   - 動的なMCPサーバー追加とカスタム設定 