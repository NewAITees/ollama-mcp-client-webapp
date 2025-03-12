from typing import Dict, Any, List, Tuple, Optional, Union
import gradio as gr
import asyncio
import json
import os
import threading
import time
import uuid
from packaging.version import parse as parse_version
import aiohttp
from contextlib import asynccontextmanager
import nest_asyncio
from .config import load_server_config, create_server_parameters
from .mcp_client import list_server_tools, call_server_tool
from .logger import logger
from .models import Tool, ToolResponse
from unittest.mock import MagicMock

# グローバル変数
server_config: Dict[str, Any] = {}
server_parameters: Dict[str, Any] = {}
http_session: Optional[aiohttp.ClientSession] = None
# HTTPリクエスト制限用のセマフォ
http_semaphore = None  # アプリケーション初期化時に作成

# イベントループの初期化
nest_asyncio.apply()  # 既存のイベントループを再利用可能にする

# スレッドセーフなツールデータ管理
class ThreadSafeToolStore:
    def __init__(self):
        self._tools = {}
        self._lock = threading.RLock()
    
    def set_tools(self, server_name, tools):
        with self._lock:
            self._tools[server_name] = tools
    
    def get_tools(self, server_name=None):
        with self._lock:
            if server_name is None:
                return self._tools.copy()
            return self._tools.get(server_name, []).copy()
    
    def clear(self):
        with self._lock:
            self._tools.clear()

# グローバル変数の代わりにスレッドセーフなインスタンスを使用
tools_store = ThreadSafeToolStore()

# ロギングコンテキスト
@asynccontextmanager
async def task_logging_context(task_name: str):
    """非同期タスクのロギングコンテキスト"""
    task_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    logger.info(f"Task {task_id} ({task_name}) started")
    
    try:
        yield task_id
        
        elapsed = time.time() - start_time
        logger.info(f"Task {task_id} ({task_name}) completed successfully in {elapsed:.2f}s")
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Task {task_id} ({task_name}) failed after {elapsed:.2f}s: {str(e)}")
        raise

# リソース管理関連の関数
async def create_shared_session():
    """共有aiohttp.ClientSessionを作成"""
    global http_session, http_semaphore
    
    # HTTPリクエスト制限用のセマフォを初期化
    http_semaphore = asyncio.Semaphore(20)  # 最大20同時リクエスト
    
    # TCPコネクタの設定
    connector = aiohttp.TCPConnector(
        limit=100,              # 最大接続数
        limit_per_host=20,      # ホストごとの最大接続数
        enable_cleanup_closed=True,  # クローズした接続のクリーンアップ
        force_close=False,      # 接続の再利用を許可
        ttl_dns_cache=300,      # DNSキャッシュのTTL（秒）
    )
    
    # セッションの作成
    http_session = aiohttp.ClientSession(
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=60, connect=10)
    )
    return http_session

async def cleanup_shared_session():
    """共有セッションをクリーンアップ"""
    global http_session
    if http_session and not http_session.closed:
        await http_session.close()

# リトライ機能付き関数実行
async def call_with_retry_async(coro, max_retries=3, retry_delay=1.0):
    """リトライ機能付きで非同期関数を実行する"""
    retries = 0
    last_exception = None
    
    while retries < max_retries:
        try:
            return await coro
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            # ネットワークエラーやタイムアウトの場合はリトライ
            last_exception = e
            retries += 1
            if retries < max_retries:
                # 指数バックオフ（リトライ間隔を徐々に長くする）
                await asyncio.sleep(retry_delay * (2 ** (retries - 1)))
            else:
                # 最大リトライ回数に達した
                logger.error(f"Maximum retries reached: {str(e)}")
                raise
        except Exception as e:
            # その他のエラーはリトライしない
            logger.error(f"Non-retriable error: {str(e)}")
            raise
            
    # ここに到達すべきではないが、念のため
    raise last_exception

# 非同期版関数
async def list_servers_async() -> List[str]:
    """利用可能なサーバーの一覧を非同期で返す"""
    if not server_parameters:
        logger.warning("server_parameters is empty")
        print("⚠️ server_parameters is empty")
        return []
    
    server_list = list(server_parameters.keys())
    
    logger.info(f"Available servers: {server_list}")
    print(f"📋 Available servers: {server_list}")
    return server_list

async def list_tools_async(server_name: str) -> List[Tuple[str, str]]:
    """サーバーの利用可能なツールを非同期で返す"""
    if not server_name or not server_parameters:
        logger.warning("No server name or server parameters available")
        print(f"⚠️ No server name or server parameters available: server_name={server_name}, server_parameters={server_parameters}")
        return []
    
    # リストが渡された場合は最初の要素を使用
    if isinstance(server_name, list):
        server_name = server_name[0]
        logger.warning(f"Received list input, using first element: {server_name}")
        print(f"⚠️ Received list input: {server_name}")
    
    # 事前に読み込んだツールリストを返す
    return tools_store.get_tools(server_name)

async def get_tool_schema_async(server_name: str, tool_dropdown: str) -> str:
    """ツールのスキーマを非同期で取得"""
    if not tool_dropdown:
        logger.warning("Invalid tool dropdown value")
        print("⚠️ Invalid tool dropdown value")
        return "{}"
    
    try:
        # ドロップダウンの値からスキーマを抽出
        logger.info(f"Tool dropdown value: {tool_dropdown}")
        print(f"🔍 Tool dropdown value: {tool_dropdown}")
        print(f"🔍 Tool dropdown type: {type(tool_dropdown)}")
        
        # 事前に読み込んだツールリストから対応するスキーマを探す
        tools = tools_store.get_tools(server_name)
        print(f"📦 Available tools: {tools}")
        
        for tool_name, schema in tools:
            print(f"🔍 Comparing: {tool_name} == {tool_dropdown}")
            if tool_name == tool_dropdown:
                logger.info(f"Found schema for {tool_dropdown}")
                print(f"✅ Found schema for {tool_dropdown}")
                return schema
        logger.warning("No schema found for selected tool")
        print("⚠️ No schema found for selected tool")
        return "{}"
    except Exception as e:
        error_msg = f"Error getting tool schema: {str(e)}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        return "{}"

async def call_server_tool_with_resource_limit(server_name: str, params: dict, tool_name: str, arguments: dict) -> ToolResponse:
    """リソース制限付きでサーバーツールを呼び出す"""
    global http_semaphore
    
    if http_semaphore is None:
        # セマフォがまだ初期化されていない場合は作成
        http_semaphore = asyncio.Semaphore(20)
    
    async with http_semaphore:  # セマフォで同時リクエスト数を制限
        # リトライ機能を組み込む
        return await call_with_retry_async(
            call_server_tool(server_name, params, tool_name, arguments)
        )

async def call_tool_with_timeout_async(server_name: str, tool_dropdown: Union[Tuple[str, str], List[str]], args_json: str, timeout: float = 30.0) -> str:
    """タイムアウト付きでツールを非同期で呼び出す"""
    try:
        # タスクの作成
        task = asyncio.create_task(call_tool_async(server_name, tool_dropdown, args_json))
        
        # タイムアウト付きで実行
        return await asyncio.wait_for(task, timeout=timeout)
    except asyncio.TimeoutError:
        # タスクをキャンセル
        task.cancel()
        try:
            await task  # キャンセル完了を待機
        except asyncio.CancelledError:
            pass  # 正常にキャンセルされた
        return "❌ タイムアウト: 操作が完了しませんでした"
    except Exception as e:
        return f"❌ エラー: {str(e)}"

async def call_tool_async(server_name: str, tool_dropdown: Union[Tuple[str, str], List[str]], args_json: str) -> str:
    """ツールを非同期で呼び出す"""
    if not server_name or not tool_dropdown or not server_parameters:
        return "サーバーとツールを選択してください"
    
    # ツール名を抽出（"name - description" から "name" を取得）
    if isinstance(tool_dropdown, tuple):
        tool_name = tool_dropdown[0].split(" - ")[0]
    elif isinstance(tool_dropdown, list) and len(tool_dropdown) > 0:
        tool_name = tool_dropdown[0].split(" - ")[0]
    else:
        return "無効なツールが選択されています"
    
    async with task_logging_context(f"call_tool({server_name}, {tool_name})") as task_id:
        logger.debug(f"Task {task_id}: Args: {args_json}")
        
        try:
            # JSON引数をパース
            arguments = json.loads(args_json)
            
            if server_name not in server_parameters:
                error_msg = f"Server {server_name} not found in parameters"
                logger.error(error_msg)
                return f"❌ エラー: {error_msg}"
            
            # リソース制限付きでツールを呼び出す
            result = await call_server_tool_with_resource_limit(
                server_name, 
                server_parameters[server_name],
                tool_name,
                arguments
            )
            
            # 結果を整形
            if not isinstance(result, ToolResponse):
                error_msg = f"Unexpected result type: {type(result)}"
                logger.error(error_msg)
                return f"❌ エラー: {error_msg}"
                
            if result.success:
                logger.debug(f"Task {task_id}: Completed with success")
                return f"✅ 成功:\n\n```json\n{json.dumps(result.result, indent=2, ensure_ascii=False)}\n```"
            else:
                logger.debug(f"Task {task_id}: Completed with error: {result.error}")
                return f"❌ エラー: {result.error}\n\n```json\n{json.dumps(result.log_entry, indent=2, ensure_ascii=False)}\n```"
        
        except json.JSONDecodeError:
            error_msg = "Invalid JSON in arguments"
            logger.error(error_msg)
            return "❌ エラー: 引数のJSONが無効です"
        except Exception as e:
            error_msg = f"Tool call failed: {str(e)}"
            logger.exception(error_msg)
            return f"❌ エラー: {str(e)}"

async def initialize_tools_async() -> None:
    """初期化時にすべてのツールを非同期で読み込む"""
    try:
        for server_name in server_parameters.keys():
            logger.info(f"Loading tools for server: {server_name}")
            print(f"🔍 Loading tools for server: {server_name}")
            
            # 非同期呼び出し
            tools = await list_server_tools(server_name, server_parameters[server_name])
            
            # Gradioのドロップダウン用に変換
            converted_tools = [(f"{tool.name} - {tool.description}", tool.schema) for tool in tools]
            
            # スレッドセーフに保存
            tools_store.set_tools(server_name, converted_tools)
            
            logger.info(f"Loaded {len(converted_tools)} tools for {server_name}")
            print(f"✅ Loaded {len(converted_tools)} tools for {server_name}")
    except Exception as e:
        error_msg = f"Error initializing tools: {str(e)}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        tools_store.clear()

# 同期版関数（既存のGradioコンポーネントとの互換性のため）
def list_servers() -> List[str]:
    """利用可能なサーバーの一覧を返す（表示値＝内部値）"""
    return asyncio.get_event_loop().run_until_complete(list_servers_async())

def list_tools(server_name: str) -> List[Tuple[str, str]]:
    """サーバーの利用可能なツールを返す"""
    return asyncio.get_event_loop().run_until_complete(list_tools_async(server_name))

def get_tool_schema(server_name: str, tool_dropdown: str) -> str:
    """ツールのスキーマを取得"""
    return asyncio.get_event_loop().run_until_complete(get_tool_schema_async(server_name, tool_dropdown))

def call_tool(server_name: str, tool_dropdown: Tuple[str, str], args_json: str) -> str:
    """ツールを呼び出す"""
    return asyncio.get_event_loop().run_until_complete(call_tool_async(server_name, tool_dropdown, args_json))

def initialize_tools() -> None:
    """初期化時にすべてのツールを読み込む"""
    asyncio.get_event_loop().run_until_complete(initialize_tools_async())

def create_app(test_mode: bool = False) -> gr.Blocks:
    """Gradioアプリケーションを作成"""
    global server_config, server_parameters
    
    # 設定の読み込み
    try:
        server_config = load_server_config()
        server_parameters = create_server_parameters(server_config)
        logger.info(f"Loaded server config: {server_config}")
        logger.info(f"Created server parameters: {server_parameters}")
        print(f"✅ Loaded server config: {server_config}")
        print(f"✅ Created server parameters: {server_parameters}")
        
        # 初期化時にすべてのツールを読み込む
        initialize_tools()
    except Exception as e:
        error_msg = f"Error loading server config: {str(e)}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        server_config = {}
        server_parameters = {}
        tools_store.clear()

    with gr.Blocks(title="MCP Test Harness", theme=gr.themes.Default()) as app:
        gr.Markdown("# MCPテストハーネス")
        gr.Markdown("MCPサーバーとの通信をテストし、結果をログに記録します。")
        
        with gr.Row():
            with gr.Column(scale=1):
                # サーバー・ツール選択
                server_list = list_servers()  # 同期関数として呼び出し
                server_dropdown = gr.Dropdown(
                    label="MCPサーバー", 
                    choices=server_list,  # 直接リストを設定
                    interactive=True,
                    allow_custom_value=True,
                    value=None,
                    info="利用可能なMCPサーバーを選択してください"
                )
                print("🎯 Created server_dropdown component")
                
                tool_dropdown = gr.Dropdown(
                    label="ツール", 
                    choices=[], 
                    interactive=True,
                    allow_custom_value=False,
                    value=None
                )
                print("🎯 Created tool_dropdown component")
                
                # スキーマ表示
                schema_json = gr.JSON(
                    label="ツールスキーマ", 
                    value={}
                )
                
                # 引数入力
                args_input = gr.Code(
                    label="引数 (JSON)", 
                    language="json", 
                    value="{}"
                )
                
                # 実行ボタン
                execute_btn = gr.Button("ツールを実行", variant="primary")
            
            with gr.Column(scale=1):
                # 結果表示
                result_output = gr.Markdown(
                    label="結果", 
                    value="結果がここに表示されます"
                )
                
                # ログ表示
                with gr.Accordion("ログ", open=False):
                    log_output = gr.Textbox(
                        label="ログ", 
                        value="", 
                        lines=10,
                        max_lines=20
                    )
                    clear_log_btn = gr.Button("ログをクリア")
        
        # Gradioのバージョンに応じたイベントハンドラの設定
        if parse_version(gr.__version__) >= parse_version("4.0"):
            # Gradio 4.0以上では非同期関数を直接使用
            print("🔄 Using async handlers (Gradio 4.0+)")
            
            # サーバー選択時のツールリスト更新
            server_dropdown.change(
                fn=list_tools_async,
                inputs=[server_dropdown],
                outputs=[tool_dropdown]
            )
            
            # ツール選択時のスキーマ更新
            tool_dropdown.change(
                fn=get_tool_schema_async,
                inputs=[server_dropdown, tool_dropdown],
                outputs=[schema_json]
            )
            
            # ツール実行
            execute_btn.click(
                fn=call_tool_with_timeout_async,  # タイムアウト付き非同期関数を使用
                inputs=[server_dropdown, tool_dropdown, args_input],
                outputs=[result_output]
            )
        else:
            # Gradio 3.x向けの同期ラッパーを使用
            print("🔄 Using sync wrappers (Gradio 3.x)")
            
            # サーバー選択時のツールリスト更新
            server_dropdown.change(
                fn=list_tools,
                inputs=[server_dropdown],
                outputs=[tool_dropdown]
            )
            
            # ツール選択時のスキーマ更新
            tool_dropdown.change(
                fn=get_tool_schema,
                inputs=[server_dropdown, tool_dropdown],
                outputs=[schema_json]
            )
            
            # ツール実行
            execute_btn.click(
                fn=call_tool,
                inputs=[server_dropdown, tool_dropdown, args_input],
                outputs=[result_output]
            )
            
        print("🎯 Set up event handlers based on Gradio version")
        
        # ログクリア
        clear_log_btn.click(
            fn=lambda: "",
            inputs=[],
            outputs=[log_output]
        )
        print("🎯 Set up clear_log_btn click event handler")
    
    return app

def launch_app(env: str = "development") -> None:
    """環境に応じたアプリケーション起動"""
    # イベントループの初期化
    loop = asyncio.get_event_loop()
    
    # 共有セッションの初期化
    loop.run_until_complete(create_shared_session())
    
    # シャットダウン時のクリーンアップを登録
    import atexit
    import signal
    
    def cleanup():
        try:
            loop.run_until_complete(cleanup_shared_session())
        except:
            logger.warning("Error during cleanup")
    
    atexit.register(cleanup)
    
    try:
        # シグナルハンドラの登録（Windows以外の場合）
        if os.name != 'nt':
            signal.signal(signal.SIGINT, lambda s, f: cleanup())
            signal.signal(signal.SIGTERM, lambda s, f: cleanup())
    except Exception as e:
        logger.warning(f"Could not set signal handlers: {e}")
    
    # Gradioアプリの作成
    app = create_app()
    
    # 環境ごとの設定
    if env == "production":
        # 本番環境設定
        queue_kwargs = {
            "max_size": 100,          # より大きなキューサイズ
            "concurrency_limit": 30,   # より多くの同時実行
            "status_update_rate": 5,   # より頻繁なステータス更新
            "api_open": False,         # APIを閉じる
        }
        launch_kwargs = {
            "server_name": "0.0.0.0",
            "server_port": int(os.environ.get("PORT", 7860)),
            "max_threads": 100,
            "quiet": True,
            "show_api": False,
            "share": False,
            "auth": os.environ.get("GRADIO_AUTH", None),  # 環境変数から認証情報を取得
            "ssl_keyfile": os.environ.get("SSL_KEY", None),
            "ssl_certfile": os.environ.get("SSL_CERT", None),
        }
        logger.info("Starting app in PRODUCTION mode")
    else:
        # 開発環境設定
        queue_kwargs = {
            "max_size": 20,
            "concurrency_limit": 10,
            "status_update_rate": 10
        }
        launch_kwargs = {
            "show_api": False,
            "share": False,
            "server_name": "0.0.0.0",
            "server_port": 7860,
            "max_threads": 40,
            "quiet": False,
            "prevent_thread_lock": False
        }
        logger.info("Starting app in DEVELOPMENT mode")
    
    # キュー設定を適用（Gradioバージョンに応じて）
    if hasattr(app, "queue"):
        # Gradio 4.0
        app.queue(**queue_kwargs)
    
    # アプリケーション起動
    app.launch(**launch_kwargs)

if __name__ == "__main__":
    # 環境変数から実行環境を取得（デフォルトは開発環境）
    environment = os.environ.get("APP_ENV", "development")
    launch_app(environment) 