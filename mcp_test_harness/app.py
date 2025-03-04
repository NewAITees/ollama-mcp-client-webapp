from typing import Dict, Any, List, Tuple, Optional
import gradio as gr
import asyncio
import json
from .config import load_server_config, create_server_parameters
from .mcp_client import list_server_tools, call_server_tool
from .logger import logger
from .models import Tool, ToolResponse
from unittest.mock import MagicMock

# グローバル変数
server_config: Optional[Dict[str, Any]] = None
server_parameters: Optional[Dict[str, Any]] = None

async def list_servers() -> List[str]:
    """利用可能なサーバーの一覧を返す"""
    if server_parameters is None:
        logger.warning("server_parameters is None")
        print("⚠️ server_parameters is None")
        return []
    server_list = list(server_parameters.keys())
    logger.info(f"Available servers: {server_list}")
    print(f"📋 Available servers: {server_list}")
    return server_list

async def list_tools(server_name: str) -> List[Tuple[str, str]]:
    """サーバーの利用可能なツールを返す"""
    if not server_name or server_parameters is None:
        logger.warning("No server name or server parameters available")
        print(f"⚠️ No server name or server parameters available: server_name={server_name}, server_parameters={server_parameters}")
        return []
    
    # リストが渡された場合は最初の要素を使用
    if isinstance(server_name, list):
        server_name = server_name[0]
        logger.warning(f"Received list input, using first element: {server_name}")
        print(f"⚠️ Received list input: {server_name}")
    
    try:
        logger.info(f"Listing tools for server: {server_name}")
        print(f"🔍 Listing tools for server: {server_name}")
        tools = await list_server_tools(server_name, server_parameters[server_name])
        logger.info(f"Received tools: {tools}")
        print(f"📦 Received tools: {tools}")
        
        # Gradioのドロップダウン用に変換
        result = [(f"{tool.name} - {tool.description}", tool.schema) for tool in tools]
        logger.info(f"Converted tools for dropdown: {result}")
        print(f"✅ Converted tools for dropdown: {result}")
        return result
    except Exception as e:
        error_msg = f"Error listing tools: {str(e)}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        return []

async def get_tool_schema(server_name: str, tool_dropdown: str) -> str:
    """ツールのスキーマを取得"""
    if not tool_dropdown:
        logger.warning("Invalid tool dropdown value")
        print("⚠️ Invalid tool dropdown value")
        return "{}"
    
    try:
        # ドロップダウンの値からスキーマを抽出
        # 値は "name - description" の形式
        logger.info(f"Tool dropdown value: {tool_dropdown}")
        print(f"🔍 Tool dropdown value: {tool_dropdown}")
        print(f"🔍 Tool dropdown type: {type(tool_dropdown)}")
        
        # ツールリストから対応するスキーマを探す
        tools = await list_tools(server_name)
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

async def call_tool(server_name: str, tool_dropdown: Tuple[str, str], args_json: str) -> str:
    """ツールを呼び出す"""
    if not server_name or not tool_dropdown or server_parameters is None:
        return "サーバーとツールを選択してください"
    
    # ツール名を抽出（"name - description" から "name" を取得）
    tool_name = tool_dropdown[0].split(" - ")[0]
    
    try:
        # JSON引数をパース
        arguments = json.loads(args_json)
        
        # ツールを呼び出し
        result = await call_server_tool(
            server_name, 
            server_parameters[server_name],
            tool_name,
            arguments
        )
        
        # 結果を整形
        if not isinstance(result, ToolResponse):
            return f"❌ エラー: 予期しない結果の型です: {type(result)}"
            
        if result.success:
            return f"✅ 成功:\n\n```json\n{json.dumps(result.result, indent=2, ensure_ascii=False)}\n```"
        else:
            return f"❌ エラー: {result.error}\n\n```json\n{json.dumps(result.log_entry, indent=2, ensure_ascii=False)}\n```"
    
    except json.JSONDecodeError:
        return "❌ エラー: 引数のJSONが無効です"
    except Exception as e:
        logger.exception("Tool call failed")
        return f"❌ エラー: {str(e)}"

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
    except Exception as e:
        error_msg = f"Error loading server config: {str(e)}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        server_config = {}
        server_parameters = {}

    with gr.Blocks(title="MCP Test Harness") as app:
        gr.Markdown("# MCPテストハーネス")
        gr.Markdown("MCPサーバーとの通信をテストし、結果をログに記録します。")
        
        with gr.Row():
            with gr.Column(scale=1):
                # サーバー・ツール選択
                server_dropdown = gr.Dropdown(
                    label="MCPサーバー", 
                    choices=[], 
                    interactive=True,
                    allow_custom_value=False,  # カスタム値を許可しない
                    value=None,  # 明示的に初期値をNoneに設定
                    type="value"  # 値を直接取得するように設定
                )
                print("🎯 Created server_dropdown component")
                
                tool_dropdown = gr.Dropdown(
                    label="ツール", 
                    choices=[], 
                    interactive=True,
                    allow_custom_value=False,  # カスタム値を許可しない
                    value=None  # 明示的に初期値をNoneに設定
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
        
        # イベントハンドラ
        server_dropdown.change(
            fn=list_tools,
            inputs=[server_dropdown],
            outputs=[tool_dropdown]
        )
        print("🎯 Set up server_dropdown change event handler")
        
        tool_dropdown.change(
            fn=get_tool_schema,
            inputs=[server_dropdown, tool_dropdown],
            outputs=[schema_json]
        )
        print("🎯 Set up tool_dropdown change event handler")
        
        execute_btn.click(
            fn=call_tool,
            inputs=[server_dropdown, tool_dropdown, args_input],
            outputs=[result_output]
        )
        print("🎯 Set up execute_btn click event handler")
        
        clear_log_btn.click(
            fn=lambda: "",
            inputs=[],
            outputs=[log_output]
        )
        print("🎯 Set up clear_log_btn click event handler")
        
        # サーバーリスト更新ボタン
        refresh_btn = gr.Button("サーバーリストを更新")
        refresh_btn.click(
            fn=list_servers,
            inputs=[],
            outputs=[server_dropdown]
        )
        print("🎯 Set up refresh_btn click event handler")
        
        # 初期化
        app.load(
            fn=list_servers,
            outputs=[server_dropdown],
            show_progress=True  # 進捗を表示
        )
        print("🎯 Set up app.load event handler")
    
    return app

def launch_app() -> None:
    """アプリケーションを起動"""
    app = create_app()
    app.launch()

if __name__ == "__main__":
    launch_app() 