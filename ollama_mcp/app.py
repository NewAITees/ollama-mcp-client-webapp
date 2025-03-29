"""
メインアプリケーションのエントリーポイント
Gradio UIとAgno統合クライアント機能を含む
"""
import argparse
import asyncio
import os
import time
import json
import io
import tempfile
from typing import List, Optional, Dict, Any, Tuple, Union, Callable
from pathlib import Path

import gradio as gr
import ollama
from PIL import Image
from loguru import logger

from ollama_mcp.agno_client import AgnoClient  # 新しい統合クライアント
from ollama_mcp.debug_module import AgnoMCPDebugger

class OllamaMCPApp:
    """
    Ollama MCP Client & Agent のメインアプリケーション
    
    主な責務:
    - Gradio UIの提供
    - Agnoクライアントとの連携
    - チャット履歴の管理
    - エラーハンドリング
    """
    def __init__(self, model_name: str = "gemma3:4b", debug_level: str = "info", direct_mode: bool = True):
        """
        OllamaMCPAppを初期化
        
        Args:
            model_name: 使用するOllamaモデル名
            debug_level: デバッグログのレベル
            direct_mode: MCPサーバーを使用せず直接Ollamaと通信するかどうか (デフォルトはTrue)
        """
        self.model_name = model_name
        self.debug_level = debug_level
        self.direct_mode = direct_mode
        # 直接モードが有効な場合は接続状態をTrueに初期化
        self.is_connected = direct_mode
        
        # Ollama公式クライアント（APIチェック用）
        try:
            self.client = ollama.Client()
        except Exception as e:
            logger.warning(f"Failed to initialize Ollama client: {e}. Please ensure Ollama is running.")
            self.client = None
            
        self.debugger = AgnoMCPDebugger(level=debug_level)
        self.integration = AgnoClient(
            model_name=model_name, 
            debug_level=debug_level,
            direct_mode=direct_mode
        )
        
        # 状態管理用の変数
        self.available_tools = []
        self.server_path = None
        self.history = []
        self.retries = 3
        
        # モデルパラメータ
        self.model_params = {
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        self.debugger.log(f"OllamaMCPApp initialized with model {model_name}", "info")
    
    async def connect_to_server(self, server_path: str) -> str:
        """MCPサーバーに接続"""
        if self.direct_mode:
            self.is_connected = True
            return "✅ Direct mode enabled. Connected to Ollama directly."
            
        if not server_path or server_path.strip() == "":
            return "❌ Server path is empty. Please provide a valid path."
        
        self.debugger.log(f"Connecting to MCP server at {server_path}", "info")
        try:
            self.available_tools = await self.integration.connect_to_server(server_path)
            self.is_connected = True
            self.server_path = server_path
            return f"✅ Successfully connected to MCP server at {server_path}. Found {len(self.available_tools)} tools."
        except Exception as e:
            self.debugger.record_error("connection_error", f"Failed to connect to server: {str(e)}")
            return f"❌ Failed to connect to MCP server: {str(e)}"
    
    def image_to_bytes(self, image: Image.Image) -> Optional[str]:
        """画像をBase64エンコードされたバイト列に変換"""
        if image is None:
            return None
        try:
            import base64
            from io import BytesIO
            
            # 画像をバイト列に変換
            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            img_bytes = buffered.getvalue()
            
            # Base64エンコード
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            return img_base64
        except Exception as e:
            self.debugger.record_error("image_conversion_error", f"Error converting image to bytes: {str(e)}")
            return None
    
    def add_message(self, text_input: str, image_input: Optional[Image.Image] = None, 
                   response_style: str = "Standard") -> Dict[str, Any]:
        """メッセージを履歴に追加"""
        message = {'role': 'user', 'content': text_input.strip()}
        
        # スタイル設定の追加
        if response_style == "Detailed":
            message['content'] += " Please provide a detailed response."
        elif response_style == "Concise":
            message['content'] += " Keep the response concise."
        elif response_style == "Creative":
            message['content'] += " Feel free to be creative with your response."
        
        # 画像の追加
        if image_input is not None:
            img_base64 = self.image_to_bytes(image_input)
            if img_base64:
                message['images'] = [img_base64]
        
        self.history.append(message)
        return message
    
    async def generate_response(self) -> str:
        """応答を生成"""
        for attempt in range(self.retries):
            try:
                # 画像パスのリストを作成（存在する場合）
                image_paths = []
                
                # 一時ディレクトリを使用して画像を処理
                with tempfile.TemporaryDirectory() as temp_dir_str:
                    temp_dir = Path(temp_dir_str)
                    
                    # 画像がメッセージに含まれている場合
                    if 'images' in self.history[-1]:
                        for i, img_base64 in enumerate(self.history[-1]['images']):
                            import base64
                            # Base64デコード
                            try:
                                img_data = base64.b64decode(img_base64)
                                img_path = temp_dir / f"image_{i}.jpg"
                                with open(img_path, "wb") as f:
                                    f.write(img_data)
                                image_paths.append(str(img_path))
                            except Exception as e:
                                self.debugger.record_error("image_decode_error", f"Failed to decode image: {str(e)}")
                                continue
                    
                    # 統合クライアントで応答を生成
                    response = await self.integration.process_query(
                        self.history[-1]['content'],
                        images=image_paths if image_paths else None
                    )
                    
                    # 一時ファイルは自動的にクリーンアップされる
                
                assistant_message = {
                    'role': 'assistant', 
                    'content': response
                }
                self.history.append(assistant_message)
                return assistant_message['content']
                
            except Exception as e:
                self.debugger.record_error("response_generation_error", 
                    f"Error generating response (attempt {attempt + 1}): {str(e)}")
                if attempt == self.retries - 1:
                    return f"Error generating response after {self.retries} attempts: {str(e)}"
        
        return "Failed to generate response after multiple attempts."
    
    async def chat_with_file(self, message: str, file: Optional[tempfile._TemporaryFileWrapper] = None, 
                           chat_history: Optional[List] = None) -> Tuple[List, str]:
        """
        メッセージと任意のファイルを処理してチャット履歴を更新
        
        Args:
            message: ユーザーからの入力メッセージ
            file: アップロードされたファイル（オプション）
            chat_history: 現在のチャット履歴
            
        Returns:
            更新されたチャット履歴とクリアされた入力フィールド
        """
        if not message and not file:
            return chat_history or [], ""
            
        chat_history = chat_history or []
        
        # 画像ファイルの確認と処理
        image = None
        if file:
            try:
                image = Image.open(file.name)
                self.debugger.log(f"Processed uploaded image: {file.name}", "debug")
            except Exception as e:
                self.debugger.record_error("image_processing_error", f"Error processing image: {str(e)}")
                chat_history.append((message, f"Error processing image: {str(e)}"))
                return chat_history, ""
        
        # 接続状態の確認
        if not self.is_connected and not self.direct_mode:
            response = "⚠️ Not connected to a MCP server. Please connect first in the Settings tab."
            chat_history.append((message, response))
            return chat_history, ""
        
        # メッセージを履歴に追加
        chat_history.append((message, None))
        
        # 画像がある場合は画像を含むメッセージを追加
        self.add_message(message, image)
        
        # 応答を生成
        try:
            response = await self.generate_response()
            chat_history[-1] = (message, response)
        except Exception as e:
            self.debugger.record_error("chat_error", f"Error in chat: {str(e)}")
            chat_history[-1] = (message, f"Error: {str(e)}")
        
        return chat_history, ""
    
    async def handle_server_connection(self, server_path: str) -> str:
        """
        サーバー接続ハンドラ
        
        Args:
            server_path: MCPサーバーのパス
            
        Returns:
            接続結果メッセージ
        """
        return await self.connect_to_server(server_path)
    
    def update_model_params(self, temperature: float, top_p: float) -> str:
        """
        モデルパラメータを更新
        
        Args:
            temperature: 温度パラメータ
            top_p: top_pパラメータ
            
        Returns:
            更新結果メッセージ
        """
        self.model_params.update({
            "temperature": temperature,
            "top_p": top_p
        })
        
        self.integration.set_model_parameters(self.model_params)
        return f"✅ Model parameters updated: temperature={temperature}, top_p={top_p}"
    
    def change_model(self, model_name: str) -> str:
        """
        使用するモデルを変更
        
        Args:
            model_name: 新しいモデル名
            
        Returns:
            変更結果メッセージ
        """
        self.model_name = model_name
        self.integration.set_model(model_name)
        return f"✅ Model changed to {model_name}"
    
    async def get_available_models(self) -> List[str]:
        """
        利用可能なモデルを取得
        
        Returns:
            モデル名のリスト
        """
        try:
            if not self.client:
                return ["Failed to get models - Ollama client not initialized"]
            
            # 正しい方法でモデル一覧を取得
            try:
                # ollama list コマンドを使用してモデル一覧を取得 (最も信頼性の高い方法)
                import subprocess
                result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, check=True)
                
                # 出力行を解析
                lines = result.stdout.strip().split('\n')
                
                # ヘッダー行をスキップ (NAME TAG ID など)
                if len(lines) > 1:
                    models = []
                    for line in lines[1:]:  # ヘッダー行をスキップ
                        parts = line.split()
                        if parts:
                            models.append(parts[0])  # 最初の列はモデル名
                    
                    if models:
                        self.debugger.log(f"Models from CLI: {models}", "info")
                        return models
            except Exception as e:
                self.debugger.log(f"CLI model fetch failed: {str(e)}", "warning")
            
            # CLI が失敗した場合は API を試す
            try:
                # Python クライアントのネイティブメソッドを使用
                response = await asyncio.to_thread(lambda: self.client.list())
                
                # response オブジェクトを適切に処理する
                models = []
                
                # Python クライアントの実装に依存しないように、
                # 様々な可能性を試す
                if hasattr(response, 'models'):
                    # models 属性がある場合
                    model_list = response.models
                    for model in model_list:
                        if hasattr(model, 'name'):
                            models.append(model.name)
                        elif hasattr(model, 'model'):
                            models.append(model.model)
                
                if models:
                    self.debugger.log(f"Models from API: {models}", "info")
                    return models
            except Exception as e:
                self.debugger.log(f"API model fetch failed: {str(e)}", "warning")
            
            # どちらの方法も失敗した場合はデフォルト値を返す
            default_models = ["gemma3:27b", "llama3", "mistral", "mixtral"]
            self.debugger.log(f"Using default model list: {default_models}", "warning")
            return default_models
            
        except Exception as e:
            self.debugger.record_error("model_list_error", f"Error getting available models: {str(e)}")
            return ["gemma3:27b", "llama3", "mistral", "mixtral"]
    
    async def get_recent_logs(self, count: int = 20) -> List[Dict[str, Any]]:
        """
        最近のログを取得
        
        Args:
            count: 取得するログの数
            
        Returns:
            ログエントリのリスト
        """
        return self.debugger.get_recent_logs(count)
    
    async def get_tool_calls(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        ツールコールを取得
        
        Args:
            count: 取得するツールコールの数
            
        Returns:
            ツールコールのリスト
        """
        return self.debugger.get_tool_calls(count)
    
    async def get_errors(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        エラーを取得
        
        Args:
            count: 取得するエラーの数
            
        Returns:
            エラーのリスト
        """
        return self.debugger.get_errors(count)
    
    async def get_tools_table(self) -> List[List[str]]:
        """
        ツール情報をテーブル形式で取得
        
        Returns:
            ツール情報のテーブル（ヘッダーと行のリスト）
        """
        if not self.available_tools:
            return [["No tools available"]]
            
        # ヘッダー行とデータ行を含むリストを作成
        table = [["Name", "Description", "Parameters"]]
        
        for tool in self.available_tools:
            name = tool.get("name", "Unknown")
            description = tool.get("description", "No description")
            
            # パラメータをフォーマット
            params = []
            if "inputSchema" in tool and "properties" in tool["inputSchema"]:
                for param_name, param_info in tool["inputSchema"]["properties"].items():
                    param_type = param_info.get("type", "any")
                    param_desc = param_info.get("description", "")
                    params.append(f"{param_name} ({param_type}): {param_desc}")
            
            params_str = "\n".join(params) if params else "No parameters"
            
            table.append([name, description, params_str])
        
        return table
    
    def build_ui(self) -> gr.Blocks:
        """
        Gradio UIを構築
        
        Returns:
            Gradioアプリケーション
        """
        with gr.Blocks(title="Ollama MCP Client & Agent") as app:
            # ヘッダー
            gr.Markdown(f"# Ollama MCP Client & Agent")
            gr.Markdown(f"## Using model: {self.model_name}")
            
            # タブ構造
            with gr.Tabs() as tabs:
                # チャットタブ
                with gr.Tab("Chat"):
                    with gr.Row():
                        with gr.Column(scale=4):
                            chat_interface = gr.Chatbot(height=600)
                            
                            with gr.Row():
                                with gr.Column(scale=8):
                                    msg_input = gr.Textbox(
                                        show_label=False,
                                        placeholder="Type your message here...",
                                        lines=2
                                    )
                                with gr.Column(scale=1):
                                    send_btn = gr.Button("Send")
                            
                            with gr.Row():
                                file_input = gr.File(label="Upload Image (Optional)")
                                clear_btn = gr.Button("Clear Chat")
                        
                        with gr.Column(scale=1):
                            # 接続状態表示を更新
                            status_text = "Direct mode (Connected)" if self.direct_mode else "Not connected"
                            status_color = "green" if self.direct_mode else "red"
                            connection_status = gr.Markdown(
                                f"<div style='color: {status_color};'>Status: {status_text}</div>"
                            )
                    
                    # イベントハンドラ
                    send_btn.click(
                        fn=self.chat_with_file,
                        inputs=[msg_input, file_input, chat_interface],
                        outputs=[chat_interface, msg_input]
                    )
                    
                    msg_input.submit(
                        fn=self.chat_with_file,
                        inputs=[msg_input, file_input, chat_interface],
                        outputs=[chat_interface, msg_input]
                    )
                    
                    clear_btn.click(
                        fn=lambda: ([], ""),
                        inputs=None,
                        outputs=[chat_interface, msg_input]
                    )
                
                # デバッグタブ
                with gr.Tab("Debug"):
                    with gr.Tabs() as debug_tabs:
                        with gr.Tab("Logs"):
                            logs_output = gr.JSON(label="Recent Logs")
                            refresh_logs = gr.Button("Refresh Logs")
                            
                            refresh_logs.click(
                                fn=self.get_recent_logs,
                                inputs=[],
                                outputs=[logs_output]
                            )
                        
                        with gr.Tab("Tool Calls"):
                            tool_calls_output = gr.JSON(label="Tool Calls")
                            refresh_tools = gr.Button("Refresh Tool Calls")
                            
                            refresh_tools.click(
                                fn=self.get_tool_calls,
                                inputs=[],
                                outputs=[tool_calls_output]
                            )
                        
                        with gr.Tab("Errors"):
                            errors_output = gr.JSON(label="Errors")
                            refresh_errors = gr.Button("Refresh Errors")
                            
                            refresh_errors.click(
                                fn=self.get_errors,
                                inputs=[],
                                outputs=[errors_output]
                            )
                
                # ツールタブ
                with gr.Tab("Tools"):
                    tools_table = gr.Dataframe(
                        headers=["Name", "Description", "Parameters"],
                        label="Available Tools"
                    )
                    refresh_tools_table = gr.Button("Refresh Tools")
                    
                    refresh_tools_table.click(
                        fn=self.get_tools_table,
                        inputs=[],
                        outputs=[tools_table]
                    )
                
                # 設定タブ
                with gr.Tab("Settings"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("## Server Connection")
                            
                            # 直接モード設定を追加
                            direct_mode_checkbox = gr.Checkbox(
                                label="Direct Mode (直接Ollamaと通信)",
                                value=self.direct_mode,
                                info="MCPサーバーを使わずに直接Ollamaと通信します"
                            )
                            
                            server_path = gr.Textbox(
                                label="Server Path",
                                placeholder="Enter path to MCP server file or URL",
                                interactive=not self.direct_mode
                            )
                            connect_btn = gr.Button("Connect", interactive=not self.direct_mode)
                            connection_result = gr.Markdown(
                                f"{'✅ Direct mode enabled. Connected to Ollama directly.' if self.direct_mode else ''}"
                            )
                            
                            # 直接モード切り替え関数
                            def toggle_direct_mode(direct_mode):
                                self.direct_mode = direct_mode
                                self.integration.direct_mode = direct_mode
                                # 接続状態を設定
                                self.is_connected = direct_mode
                                
                                # ステータス表示テキストの更新
                                status_text = "Direct mode (Connected)" if direct_mode else "Not connected"
                                status_color = "green" if direct_mode else "red"
                                
                                return {
                                    server_path: gr.update(interactive=not direct_mode),
                                    connect_btn: gr.update(interactive=not direct_mode),
                                    connection_result: "✅ Direct mode enabled. Connected to Ollama directly." if direct_mode else "",
                                    connection_status: f"<div style='color: {status_color};'>Status: {status_text}</div>"
                                }
                            
                            direct_mode_checkbox.change(
                                fn=toggle_direct_mode,
                                inputs=[direct_mode_checkbox],
                                outputs=[server_path, connect_btn, connection_result, connection_status]
                            )
                            
                            connect_btn.click(
                                fn=self.handle_server_connection,
                                inputs=[server_path],
                                outputs=[connection_result]
                            )
                        
                        with gr.Column():
                            gr.Markdown("## Model Settings")
                            
                            # モデル選択
                            model_dropdown = gr.Dropdown(
                                label="Select Model",
                                choices=["Loading models..."],
                                value=self.model_name
                            )
                            
                            # すぐにモデル一覧を取得するコード
                            app.load(
                                fn=self.get_available_models,
                                inputs=None,
                                outputs=model_dropdown
                            )
                            
                            change_model_btn = gr.Button("Change Model")
                            model_result = gr.Markdown("")
                            
                            # モデルパラメータ設定
                            gr.Markdown("### Model Parameters")
                            temperature = gr.Slider(
                                minimum=0.0,
                                maximum=1.0,
                                value=self.model_params["temperature"],
                                step=0.05,
                                label="Temperature"
                            )
                            
                            top_p = gr.Slider(
                                minimum=0.0,
                                maximum=1.0,
                                value=self.model_params["top_p"],
                                step=0.05,
                                label="Top P"
                            )
                            
                            update_params_btn = gr.Button("Update Parameters")
                            params_result = gr.Markdown("")
                            
                            # イベントハンドラ
                            change_model_btn.click(
                                fn=self.change_model,
                                inputs=[model_dropdown],
                                outputs=[model_result]
                            )
                            
                            update_params_btn.click(
                                fn=self.update_model_params,
                                inputs=[temperature, top_p],
                                outputs=[params_result]
                            )
            
            # フッター
            gr.Markdown("---")
            gr.Markdown("Ollama MCP Client & Agent - powered by Agno Framework")
        
        return app
    
    def run(self, server_path: Optional[str] = None, port: int = 7860, share: bool = False) -> None:
        """
        アプリケーションを実行
        
        Args:
            server_path: MCPサーバーのパス（オプション）
            port: UIのポート番号
            share: 共有リンクを生成するかどうか
        """
        app = self.build_ui()
        
        # サーバーパスが指定されていれば自動接続
        if server_path:
            async def connect_on_start():
                await self.connect_to_server(server_path)
            
            app.load(fn=connect_on_start, inputs=None, outputs=None)
        
        # アプリケーションを起動
        app.launch(server_port=port, share=share)

def main():
    """
    メインエントリーポイント
    コマンドライン引数を処理してアプリケーションを起動
    """
    parser = argparse.ArgumentParser(description="Ollama MCP Client & Agent")
    parser.add_argument("--model", type=str, default="gemma3:27b", help="Ollama model to use")
    parser.add_argument("--server", type=str, help="Path to MCP server file or URL")
    parser.add_argument("--debug", type=str, default="info", choices=["debug", "info", "warning", "error"], 
                        help="Debug log level")
    parser.add_argument("--port", type=int, default=7860, help="UI port")
    parser.add_argument("--share", action="store_true", help="Generate a public share link")
    parser.add_argument("--direct", action="store_false", help="Use direct mode (no MCP server)")
    
    args = parser.parse_args()
    
    app = OllamaMCPApp(
        model_name=args.model,
        debug_level=args.debug,
        direct_mode=args.direct
    )
    
    app.run(server_path=args.server, port=args.port, share=args.share)

if __name__ == "__main__":
    main()