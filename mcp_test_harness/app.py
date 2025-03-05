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
server_config: Dict[str, Any] = {}
server_parameters: Dict[str, Any] = {}
all_tools: Dict[str, List[Tuple[str, str]]] = {}  # サーバー名 -> ツールリスト

def list_servers() -> List[str]:
    """利用可能なサーバーの一覧を返す（表示値＝内部値）"""
    if not server_parameters:
        logger.warning("server_parameters is empty")
        print("⚠️ server_parameters is empty")
        return []
    
    server_list = list(server_parameters.keys())
    
    logger.info(f"Available servers: {server_list}")
    print(f"📋 Available servers: {server_list}")
    return server_list

def list_tools(server_name: str) -> List[Tuple[str, str]]:
    """サーバーの利用可能なツールを返す"""
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
    return all_tools.get(server_name, [])

def get_tool_schema(server_name: str, tool_dropdown: str) -> str:
    """ツールのスキーマを取得"""
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
        tools = all_tools.get(server_name, [])
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

def call_tool(server_name: str, tool_dropdown: Tuple[str, str], args_json: str) -> str:
    """ツールを呼び出す"""
    if not server_name or not tool_dropdown or not server_parameters:
        return "サーバーとツールを選択してください"
    
    # ツール名を抽出（"name - description" から "name" を取得）
    tool_name = tool_dropdown[0].split(" - ")[0]
    
    try:
        # JSON引数をパース
        arguments = json.loads(args_json)
        
        if server_name not in server_parameters:
            error_msg = f"Server {server_name} not found in parameters"
            logger.error(error_msg)
            return f"❌ エラー: {error_msg}"
        
        # 非同期関数を同期呼び出し
        result = asyncio.run(call_server_tool(
            server_name, 
            server_parameters[server_name],
            tool_name,
            arguments
        ))
        
        # 結果を整形
        if not isinstance(result, ToolResponse):
            error_msg = f"Unexpected result type: {type(result)}"
            logger.error(error_msg)
            return f"❌ エラー: {error_msg}"
            
        if result.success:
            return f"✅ 成功:\n\n```json\n{json.dumps(result.result, indent=2, ensure_ascii=False)}\n```"
        else:
            return f"❌ エラー: {result.error}\n\n```json\n{json.dumps(result.log_entry, indent=2, ensure_ascii=False)}\n```"
    
    except json.JSONDecodeError:
        error_msg = "Invalid JSON in arguments"
        logger.error(error_msg)
        return "❌ エラー: 引数のJSONが無効です"
    except Exception as e:
        error_msg = f"Tool call failed: {str(e)}"
        logger.exception(error_msg)
        return f"❌ エラー: {str(e)}"

def initialize_tools() -> None:
    """初期化時にすべてのツールを読み込む"""
    global all_tools
    
    try:
        for server_name in server_parameters.keys():
            logger.info(f"Loading tools for server: {server_name}")
            print(f"🔍 Loading tools for server: {server_name}")
            
            # 非同期関数を同期呼び出し
            tools = asyncio.run(list_server_tools(server_name, server_parameters[server_name]))
            
            # Gradioのドロップダウン用に変換
            converted_tools = [(f"{tool.name} - {tool.description}", tool.schema) for tool in tools]
            
            all_tools[server_name] = converted_tools
            logger.info(f"Loaded {len(converted_tools)} tools for {server_name}")
            print(f"✅ Loaded {len(converted_tools)} tools for {server_name}")
    except Exception as e:
        error_msg = f"Error initializing tools: {str(e)}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        all_tools = {}

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
        all_tools = {}

    with gr.Blocks(title="MCP Test Harness") as app:
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
        
        # サーバー選択時のツールリスト更新
        server_dropdown.change(
            fn=list_tools,
            inputs=[server_dropdown],
            outputs=[tool_dropdown]
        )
        print("🎯 Set up server_dropdown change event handler")
        
        # ツール選択時のスキーマ更新
        tool_dropdown.change(
            fn=get_tool_schema,
            inputs=[server_dropdown, tool_dropdown],
            outputs=[schema_json]
        )
        print("🎯 Set up tool_dropdown change event handler")
        
        # ツール実行
        execute_btn.click(
            fn=call_tool,
            inputs=[server_dropdown, tool_dropdown, args_input],
            outputs=[result_output]
        )
        print("🎯 Set up execute_btn click event handler")
        
        # ログクリア
        clear_log_btn.click(
            fn=lambda: "",
            inputs=[],
            outputs=[log_output]
        )
        print("🎯 Set up clear_log_btn click event handler")
    
    return app

def launch_app() -> None:
    """アプリケーションを起動"""
    app = create_app()
    app.launch()

if __name__ == "__main__":
    launch_app() 