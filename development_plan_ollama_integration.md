# MCP Test Harness拡張開発計画: Ollama統合によるAIエージェント対応MCP通信機能

## 1. 概要と目的

MCPテストハーネスにOllamaを統合し、AIエージェントがMCPサーバーとプログラマティックに通信できる機能を実装する。これにより、人間のユーザーだけでなく、AIエージェントによるサーバーツールの呼び出しとレスポンス処理が可能になる。

## 2. 設計方針

### 2.1 アーキテクチャ

1. **AIエージェントレイヤー**
   - Ollamaクライアント統合モジュール
   - プロンプトテンプレート管理システム
   - コンテキスト管理メカニズム

2. **インターフェースレイヤー**
   - 人間↔MCPサーバー直接通信パス（既存機能）
   - 人間→AIエージェント→MCPサーバー通信パス（新機能）
   - AIエージェント→MCPサーバー自動通信パス（新機能）

3. **統合レイヤー**
   - 統一されたレスポンス処理機構
   - 会話履歴とツール実行ログの統合管理

### 2.2 コンポーネント詳細

#### a. Ollamaクライアントモジュール
```python
class OllamaClient:
    def __init__(self, model_name="mistral:latest"):
        self.model_name = model_name
        self.api_base = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
        self.session = None
        self.conversation_history = []

    async def initialize(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    async def generate_response(self, prompt, system_message=None, tools=None):
        # Ollamaへのリクエスト実装
        # tools情報をFunction Callingフォーマットで渡す
```

#### b. MCP-AIエージェント連携モジュール
```python
class MCPAgentBridge:
    def __init__(self, ollama_client, mcp_client):
        self.ollama_client = ollama_client
        self.mcp_client = mcp_client
        self.tool_registry = {}

    async def register_mcp_tools(self, server_name):
        # MCPサーバーからツール情報を取得し、AIエージェントに登録可能な形式に変換
        tools = await list_server_tools(server_name, server_parameters[server_name])
        self.tool_registry[server_name] = self._convert_to_agent_tools(tools)
        return self.tool_registry[server_name]

    def _convert_to_agent_tools(self, mcp_tools):
        # MCPツール定義をFunction Calling互換フォーマットに変換
```

#### c. Gradioインターフェース拡張
```python
def create_app(test_mode: bool = False) -> gr.Blocks:
    # 既存のコード...
    
    # AIエージェント関連のUI追加
    with gr.Tab("AIエージェント"):
        with gr.Row():
            with gr.Column(scale=1):
                agent_server_dropdown = gr.Dropdown(
                    label="対象MCPサーバー",
                    choices=server_list,
                    interactive=True
                )
                model_dropdown = gr.Dropdown(
                    label="Ollamaモデル",
                    choices=["mistral:latest", "llama3:latest", "deepseek-r1:14b"],
                    value="mistral:latest",
                    interactive=True
                )
                system_message = gr.Textbox(
                    label="システムメッセージ",
                    lines=3,
                    value="あなたはMCPサーバーと通信できるAIアシスタントです。"
                )
            
            with gr.Column(scale=2):
                chat_history = gr.Chatbot(label="会話履歴")
                user_input = gr.Textbox(label="メッセージ", placeholder="MCPサーバーへの指示を入力...")
                submit_btn = gr.Button("送信", variant="primary")
                clear_btn = gr.Button("会話をクリア")
```

## 3. 実装ロードマップ

### フェーズ1: 基盤実装（所要期間: 2週間）
1. Ollamaとの通信クライアントモジュール作成（3日）
2. MCPツールをAIエージェント向けFunction Calling形式に変換する機構（4日）
3. Gradio UIの拡張とインテグレーション（3日）
4. 会話履歴とツール実行結果の統合表示（4日）

### フェーズ2: 拡張機能（所要期間: 2週間）
1. 複数回のツール呼び出しを含むマルチターン会話サポート（5日）
2. プロンプトテンプレートとシステムメッセージの管理機能（3日）
3. ツール呼び出し結果のキャッシュメカニズム（3日）
4. AIエージェント向けのカスタムツールの追加（ファイル読み込み等）（3日）

### フェーズ3: 洗練と最適化（所要期間: 1週間）
1. エラーハンドリングの改善（2日）
2. パフォーマンス最適化（2日）
3. ユーザビリティ改善（2日）
4. ドキュメント整備（1日）

## 4. 技術要件

- **依存ライブラリ**:
  - ollama-python: ^0.1.0（Ollamaクライアント）
  - pydantic: ^2.6.0（スキーマバリデーション）
  - aiohttp: ^3.11.0（非同期HTTP通信）

- **実行環境**:
  - Ollamaサーバーが動作するマシンへのネットワークアクセス
  - 十分なメモリ（最低8GB、推奨16GB以上）

## 5. 期待される効果と利点

1. **開発効率の向上**:
   - AIエージェントによるMCPサーバーとの自動対話
   - 複雑なツール呼び出しシーケンスの自動化

2. **インタラクション品質の向上**:
   - 自然言語によるMCPサーバーとの対話
   - 複雑なパラメータ設定のAIアシスト

3. **学習と実験**:
   - AIエージェントのMCPツール利用パターンの観察
   - 効果的なツール設計へのフィードバック獲得

## 6. リスクと対策

1. **Ollamaモデルの性能制約**:
   - リスク: ローカルで実行するモデルはクラウドベースのモデルより性能が限られる
   - 対策: 最適化されたモデルの選定と、プロンプトエンジニアリングによる性能向上

2. **資源要件**:
   - リスク: 大きなモデルは大量のリソースを消費しパフォーマンスが低下する
   - 対策: 軽量モデルのオプション提供と、リソース使用量モニタリング機能の追加

3. **ツール利用の正確性**:
   - リスク: AIモデルが不正確なツール呼び出しを行う可能性
   - 対策: パラメータバリデーション強化と、重要操作の人間による承認ステップ追加

## 7. 拡張可能性

1. **複数LLMバックエンド対応**:
   - OpenAI APIやHugging Face Inference API等への拡張

2. **ツール生成機能**:
   - AIによるMCPツール定義の自動生成と提案

3. **協調作業モード**:
   - 複数AIエージェントと人間が協力してタスクを遂行する枠組み 