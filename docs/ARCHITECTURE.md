# アーキテクチャ概要

このドキュメントは Ollama MCP Client & Agent の全体的なアーキテクチャについて説明します。

## システム概要

Ollama MCP Client & Agent は、Model Context Protocol (MCP) サーバーと Agno フレームワークを統合し、マルチモーダル対応の拡張可能なエージェントフレームワークを提供するシステムです。

```mermaid
graph TB
    subgraph "ユーザー"
        UI[Gradio Web UI]
    end
    
    subgraph "Ollama MCP Client"
        Client[MCP クライアントコア]
        AgnoAgent[Agno エージェント]
        Tools[ツール実行エンジン]
        Debug[デバッグモジュール]
        Memory[メモリ管理]
        Knowledge[知識ベース]
        Multimodal[マルチモーダル処理]
    end
    
    subgraph "外部システム"
        MCP[MCP サーバー]
        Models[AI モデル]
    end
    
    UI <--> Client
    UI <--> Debug
    UI <--> AgnoAgent
    
    Client <--> MCP
    AgnoAgent <--> Models
    Client <--> AgnoAgent
    Client <--> Tools
    Tools <--> AgnoAgent
    Debug <--> Client
    Debug <--> Tools
    Debug <--> AgnoAgent
    
    AgnoAgent <--> Memory
    AgnoAgent <--> Knowledge
    AgnoAgent <--> Multimodal
    
    style Client fill:#bbdefb,stroke:#1976d2
    style AgnoAgent fill:#c8e6c9,stroke:#4caf50
    style Tools fill:#ffecb3,stroke:#ffa000
    style Debug fill:#e1bee7,stroke:#8e24aa
    style Memory fill:#ffcdd2,stroke:#e53935
    style Knowledge fill:#d1c4e9,stroke:#512da8
    style Multimodal fill:#b2dfdb,stroke:#00796b
```

## 主要コンポーネント

### 1. MCP クライアントコア

MCP プロトコルに準拠した通信を担当するコンポーネントです。

- **Session Manager**: MCP サーバーとの接続管理
- **Message Handler**: プロトコルメッセージの処理
- **Tool Registry**: 利用可能なツールの登録と管理

### 2. Agno エージェント

Agno フレームワークを使用したエージェント機能を提供するコンポーネントです。

- **Agent Manager**: エージェントの作成と管理
- **Model Integration**: 各種AIモデルとの統合
- **Tool Execution**: ツールの実行と結果処理
- **Multimodal Processing**: テキスト、画像、音声、動画の処理

### 3. メモリ管理

エージェントのメモリと状態を管理するコンポーネントです。

- **Session Memory**: 会話セッションの管理
- **State Manager**: エージェント状態の保持
- **Context Handler**: コンテキスト情報の管理
- **Database Integration**: 永続化ストレージとの連携

### 4. 知識ベース

エージェントの知識を管理するコンポーネントです。

- **Vector Store**: ベクトルデータベースの管理
- **Document Processor**: ドキュメントの処理と保存
- **Search Engine**: 関連情報の検索
- **Knowledge Update**: 知識の更新と維持

### 5. マルチモーダル処理

各種メディアの処理を担当するコンポーネントです。

- **Image Processor**: 画像処理と分析
- **Audio Handler**: 音声処理と変換
- **Video Manager**: 動画処理と解析
- **Media Integration**: マルチメディアの統合

### 6. デバッグモジュール

詳細なロギングと問題診断機能を提供するコンポーネントです。

- **Logger**: 構造化ログの記録
- **Message Inspector**: 通信メッセージの検査
- **Tracer**: ツールコールと実行の追跡
- **Error Analyzer**: エラーパターンの分析
- **Performance Monitor**: パフォーマンスの監視と分析

### 7. Gradio Web UI

ユーザーインターフェースを提供するコンポーネントです。

- **Chat Interface**: 対話インターフェース
- **Debug View**: デバッグ情報の可視化
- **Settings Panel**: 構成管理
- **Tool Editor**: ツール定義の編集
- **Media Upload**: マルチメディアのアップロード
- **Performance Dashboard**: パフォーマンス指標の表示

## データフロー

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant UI as Gradio UI
    participant Client as MCPクライアント
    participant Agent as Agnoエージェント
    participant Memory as メモリ管理
    participant Knowledge as 知識ベース
    participant Tools as ツール実行エンジン
    participant MCP as MCPサーバー
    
    User->>UI: クエリ入力
    UI->>Client: クエリ送信
    Client->>Agent: タスク委譲
    
    Agent->>Memory: コンテキスト取得
    Memory-->>Agent: コンテキスト返却
    
    Agent->>Knowledge: 関連情報検索
    Knowledge-->>Agent: 情報返却
    
    Agent->>Tools: ツール実行リクエスト
    Tools->>MCP: ツールコール送信
    MCP->>Tools: ツール実行結果
    Tools->>Agent: 結果返却
    
    Agent->>Memory: コンテキスト更新
    Agent->>Client: 最終応答
    Client->>UI: 応答表示
    UI->>User: 結果提示
```

## フォルダ構成

```mermaid
graph TD
    A[ollama-mcp-client] --> B[app.py]
    A --> C[requirements.txt]
    A --> D[docs/]
    A --> E[ollama_mcp/]
    
    E --> E1[__init__.py]
    E --> E2[client.py]
    E --> E3[agent.py]
    E --> E4[debug.py]
    E --> E5[tools.py]
    E --> E6[models.py]
    E --> E7[ui/]
    
    E7 --> E7A[__init__.py]
    E7 --> E7B[app.py]
    E7 --> E7C[components.py]
    E7 --> E7D[pages/]
    E7 --> E7E[assets/]
    
    A --> F[examples/]
    A --> G[tests/]
    
    style A fill:#f9f9f9,stroke:#999
    style E fill:#bbdefb,stroke:#1976d2
    style E7 fill:#c8e6c9,stroke:#4caf50
```

## 技術選定

| コンポーネント | 技術 | 選定理由 |
|----------------|------|----------|
| バックエンド言語 | Python 3.10 | 機械学習ライブラリとの広範な互換性、asyncio での非同期処理サポート |
| エージェントフレームワーク | Agno | 軽量で高速、マルチモーダル対応、モデル非依存の設計 |
| MCP クライアント | 純正 Python | MCP プロトコルとの直接統合、柔軟性の確保 |
| ウェブ UI | Gradio | 迅速な UI 開発、ML プロジェクトとの相性の良さ、コンポーネント豊富 |
| 依存関係管理 | uv | 高速なパッケージインストール、仮想環境管理の容易さ |
| 非同期処理 | asyncio | 効率的な I/O 処理、複数の接続とリクエストの並行処理 |
| テスト | pytest | 豊富なテスト機能、asyncio 対応のテストサポート |
| ロギング | loguru | 構造化ログ、非同期サポート、使いやすいAPI |

## アーキテクチャの原則

1. **モジュール性**: 機能を明確に分離し、独立して開発・テスト可能なコンポーネント設計
2. **拡張性**: プラグインやカスタム拡張が容易な柔軟な基盤
3. **透明性**: デバッグのために内部動作を可視化する仕組み
4. **使いやすさ**: 開発者と一般ユーザーの両方にとって直感的なインターフェース
5. **堅牢性**: エラー処理と回復メカニズムの組み込み
6. **パフォーマンス**: 高速な処理と効率的なリソース利用
7. **マルチモーダル**: 各種メディアの効率的な処理と統合

このアーキテクチャにより、MCPサーバーとAgnoフレームワークを効率的に統合し、高度なマルチモーダルエージェント機能を提供することが可能になります。

## MCPサーバー情報可視化コンポーネント

```mermaid
graph TD
    subgraph "MCPサーバー可視化"
        VS[可視化サブシステム]
        SM[状態モニター]
        TM[ツール使用モニター]
        PM[パフォーマンスモニター]
        EM[エラーモニター]
    end
    
    subgraph "データ収集"
        DC[データコレクター]
        MP[メトリクスプロセッサー]
        AP[アラートプロセッサー]
    end
    
    subgraph "データストア"
        TS[時系列データ]
        ES[イベントストア]
        MS[メトリクスストア]
    end
    
    VS --> SM
    VS --> TM
    VS --> PM
    VS --> EM
    
    SM --> DC
    TM --> DC
    PM --> DC
    EM --> DC
    
    DC --> MP
    DC --> AP
    
    MP --> TS
    MP --> MS
    AP --> ES
    
    style VS fill:#bbdefb,stroke:#1976d2
    style DC fill:#c8e6c9,stroke:#4caf50
    style MP fill:#ffecb3,stroke:#ffa000
    style AP fill:#e1bee7,stroke:#8e24aa
    style TS fill:#ffcdd2,stroke:#e53935
    style MS fill:#d1c4e9,stroke:#512da8
    style ES fill:#b2dfdb,stroke:#00796b
```

### コンポーネントの責務

#### 可視化サブシステム
- **状態モニター**: サーバーの基本状態と接続情報の表示
- **ツール使用モニター**: ツールの使用統計と分析
- **パフォーマンスモニター**: リアルタイムパフォーマンス指標の表示
- **エラーモニター**: エラー情報の集約と分析

#### データ収集
- **データコレクター**: 各種メトリクスとイベントの収集
- **メトリクスプロセッサー**: 収集データの処理と集計
- **アラートプロセッサー**: 異常検知とアラート生成

#### データストア
- **時系列データ**: 時系列メトリクスの保存
- **イベントストア**: システムイベントの記録
- **メトリクスストア**: 集計済みメトリクスの保存

### データフロー

```mermaid
sequenceDiagram
    participant UI as UI Layer
    participant VS as Visualizer
    participant DC as DataCollector
    participant MP as MetricsProcessor
    participant DS as DataStore
    
    UI->>VS: リクエスト可視化データ
    VS->>DC: データ収集リクエスト
    DC->>MP: 生データ送信
    MP->>DS: 処理済みデータ保存
    DS-->>MP: 保存確認
    MP-->>DC: 処理完了通知
    DC-->>VS: データ返却
    VS-->>UI: 可視化データ表示
```

### フォルダ構成の更新

```mermaid
graph TD
    A[ollama-mcp-client] --> V[visualization/]
    V --> V1[__init__.py]
    V --> V2[visualizer.py]
    V --> V3[collectors/]
    V --> V4[processors/]
    V --> V5[stores/]
    
    V3 --> C1[__init__.py]
    V3 --> C2[data_collector.py]
    V3 --> C3[metrics_collector.py]
    
    V4 --> P1[__init__.py]
    V4 --> P2[metrics_processor.py]
    V4 --> P3[alert_processor.py]
    
    V5 --> S1[__init__.py]
    V5 --> S2[time_series.py]
    V5 --> S3[event_store.py]
    V5 --> S4[metrics_store.py]
    
    style A fill:#f9f9f9,stroke:#999
    style V fill:#bbdefb,stroke:#1976d2
    style V3 fill:#c8e6c9,stroke:#4caf50
    style V4 fill:#ffecb3,stroke:#ffa000
    style V5 fill:#e1bee7,stroke:#8e24aa
```