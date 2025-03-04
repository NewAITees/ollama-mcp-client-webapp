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
        return []
    return list(server_parameters.keys())

async def list_tools(server_name: str) -> List[Tuple[str, str]]:
    """サーバーの利用可能なツールを返す"""
    if not server_name or server_parameters is None:
        return []
        
    try:
        tools = await list_server_tools(server_name, server_parameters[server_name])
        # Gradioのドロップダウン用に変換
        return [(f"{tool.name} - {tool.description}", tool.schema) for tool in tools]
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        return []

async def get_tool_schema(server_name: str, tool_dropdown: Tuple[str, str]) -> str:
    """ツールのスキーマを取得"""
    if not tool_dropdown or len(tool_dropdown) < 2:
        return ""
    
    # ドロップダウンの値からツール名とスキーマを抽出
    _, schema = tool_dropdown
    return schema

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
    
    # 設定の読み込み（テストモードでなければ）
    if not test_mode:
        server_config = load_server_config()
        server_parameters = create_server_parameters(server_config)
    else:
        # テストモードの場合はダミーの設定を使用
        server_config = {"mcpServers": {"test-server": {}}}
        server_parameters = {"test-server": MagicMock()}
    
    with gr.Blocks(title="MCPテストハーネス") as app:
        gr.Markdown("# MCPテストハーネス")
        gr.Markdown("MCPサーバーとの通信をテストし、結果をログに記録します。")
        
        with gr.Row():
            with gr.Column(scale=1):
                # サーバー・ツール選択
                server_dropdown = gr.Dropdown(
                    label="MCPサーバー", 
                    choices=[], 
                    interactive=True
                )
                tool_dropdown = gr.Dropdown(
                    label="ツール", 
                    choices=[], 
                    interactive=True
                )
                
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
        
        tool_dropdown.change(
            fn=get_tool_schema,
            inputs=[server_dropdown, tool_dropdown],
            outputs=[schema_json]
        )
        
        execute_btn.click(
            fn=call_tool,
            inputs=[server_dropdown, tool_dropdown, args_input],
            outputs=[result_output]
        )
        
        clear_log_btn.click(
            fn=lambda: "",
            inputs=[],
            outputs=[log_output]
        )
        
        # 初期化
        app.load(
            fn=list_servers,
            outputs=[server_dropdown]
        )
    
    return app

def launch_app() -> None:
    """アプリケーションを起動"""
    app = create_app()
    app.launch()

if __name__ == "__main__":
    launch_app() 