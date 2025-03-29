"""
メインアプリケーションのエントリーポイント
Gradio UIとOllama MCP統合機能を含む
"""
import argparse
import asyncio
import os
import time
import json
import io
from typing import List, Optional, Dict, Any, Tuple, Union, Callable
from pathlib import Path

import gradio as gr
import ollama
from PIL import Image
from loguru import logger

from ollama_mcp.agno_integration import OllamaMCPIntegration
from ollama_mcp.agno_multimodal import AgnoMultimodalIntegration
from ollama_mcp.debug_module import AgnoMCPDebugger

class OllamaMCPApp:
    """
    Ollama MCP Client & Agent のメインアプリケーション
    
    主な責務:
    - Gradio UIの提供
    - OllamaMCPIntegrationとの連携
    - マルチモーダル機能の提供
    - チャット履歴の管理
    - エラーハンドリング
    """
    def __init__(self, model_name: str = "gemma3:4b", debug_level: str = "info"):
        """
        OllamaMCPAppを初期化
        
        Args:
            model_name: 使用するOllamaモデル名
            debug_level: デバッグログのレベル
        """
        self.model_name = model_name
        self.debug_level = debug_level
        self.client = ollama.Client()
        self.debugger = AgnoMCPDebugger(level=debug_level)
        self.integration = OllamaMCPIntegration(model_name=model_name, debug_level=debug_level)
        self.multimodal = AgnoMultimodalIntegration(model_name=model_name, debug_level=debug_level)
        
        # 状態管理用の変数
        self.is_connected = False
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
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            img_bytes = buffered.getvalue()
            img_base64 = ollama.utils.encode_image_base64(img_bytes)
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
                if self.is_connected:
                    # MCPサーバー経由で応答を生成
                    response = await self.integration.process_query(
                        self.history[-1]['content'],
                        self.history[-1].get('images', [])
                    )
                else:
                    # 直接Ollamaを使用
                    response = await self.client.chat(
                        model=self.model_name,
                        messages=self.history,
                        options={
                            "temperature": self.model_params["temperature"],
                            "top_p": self.model_params["top_p"]
                        }
                    )
                    response = response['message']['content']
                
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
    
    def get_chat_history(self) -> str:
        """チャット履歴を取得"""
        return "\n".join([
            f"{msg['role'].capitalize()}: {msg['content']}" 
            for msg in self.history
        ])
    
    def reset_chat(self) -> str:
        """チャット履歴をリセット"""
        self.history = []
        return "Chat history has been reset."
    
    def build_ui(self) -> gr.Blocks:
        """Gradio UIを構築"""
        with gr.Blocks(title="Ollama MCP Client & Agent") as app:
            gr.Markdown("# Ollama MCP Client & Agent")
            
            with gr.Tabs() as tabs:
                # チャットタブ
                with gr.TabItem("Chat"):
                    gr.Markdown("Upload an image or enter a text prompt, choose a response style, and view the generated response along with the interaction history.")
                    
                    with gr.Row():
                        with gr.Column(scale=2):
                            with gr.Row():
                                text_input = gr.Textbox(
                                    lines=3, 
                                    placeholder="Enter your question here...", 
                                    label="Text Input"
                                )
                                image_input = gr.Image(
                                    type="pil", 
                                    label="Image Input (Optional)"
                                )
                            
                            with gr.Row():
                                response_style = gr.Dropdown(
                                    ["Standard", "Detailed", "Concise", "Creative"],
                                    label="Response Style",
                                    value="Standard"
                                )
                                submit_btn = gr.Button("Submit")
                                reset_btn = gr.Button("Reset Chat")
                            
                            generated_response = gr.Textbox(
                                label="Generated Response", 
                                lines=5
                            )
                        
                        with gr.Column(scale=1):
                            gr.Markdown("### Connection Status")
                            status_md = gr.Markdown("🔴 **Not Connected**")
                            server_input = gr.Textbox(
                                label="Server Path",
                                placeholder="/path/to/mcp_server.py"
                            )
                            connect_btn = gr.Button("Connect to Server")
                            history_display = gr.Textbox(
                                label="Chat History", 
                                lines=20
                            )
                
                # デバッグタブ
                with gr.TabItem("Debug"):
                    with gr.Row():
                        debug_level_select = gr.Dropdown(
                            choices=["debug", "info", "warning", "error"],
                            value=self.debug_level,
                            label="Debug Level"
                        )
                        refresh_debug_btn = gr.Button("Refresh")
                    
                    with gr.Tabs() as debug_tabs:
                        with gr.TabItem("Logs"):
                            logs_json = gr.JSON(value=[], label="Recent Logs")
                        with gr.TabItem("Tool Calls"):
                            tool_calls_json = gr.JSON(value=[], label="Tool Calls")
                        with gr.TabItem("Errors"):
                            errors_json = gr.JSON(value=[], label="Errors")
                
                # ツールタブ
                with gr.TabItem("Tools"):
                    tools_json = gr.JSON(value=[], label="Available Tools")
                    refresh_tools_btn = gr.Button("Refresh Tools")
                
                # 設定タブ
                with gr.TabItem("Settings"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### Model Settings")
                            model_select = gr.Dropdown(
                                choices=["gemma3:4b", "gemma3:7b", "llama3:7b", 
                                        "mistral:7b", "phi3"],
                                value=self.model_name,
                                label="Model",
                                allow_custom_value=True
                            )
                            temperature = gr.Slider(
                                minimum=0.0,
                                maximum=1.0,
                                value=self.model_params["temperature"],
                                step=0.1,
                                label="Temperature"
                            )
                            top_p = gr.Slider(
                                minimum=0.0,
                                maximum=1.0,
                                value=self.model_params["top_p"],
                                step=0.1,
                                label="Top P"
                            )
                            apply_settings_btn = gr.Button("Apply Settings")
            
            async def handle_connect():
                """サーバー接続を処理"""
                result = await self.connect_to_server(server_input.value)
                if self.is_connected:
                    return result, f"🟢 **Connected to {server_input.value}**"
                else:
                    return result, "🔴 **Connection Failed**"
            
            async def handle_user_input(text_input: str, 
                                      image_input: Optional[Image.Image], 
                                      response_style: str) -> Tuple[str, str]:
                """ユーザー入力を処理"""
                if not text_input.strip() and image_input is None:
                    return "Please provide either text or an image.", self.get_chat_history()
                
                try:
                    self.add_message(text_input, image_input, response_style)
                    response = await self.generate_response()
                    history_display = self.get_chat_history()
                    return response, history_display
                except Exception as e:
                    self.debugger.record_error("user_input_error", f"Error handling user input: {str(e)}")
                    return f"An error occurred: {str(e)}", self.get_chat_history()
            
            def reset_chat_history() -> Tuple[str, None, str, str, str]:
                """チャット履歴をリセット"""
                message = self.reset_chat()
                return "", None, "Standard", message, ""
            
            async def handle_refresh_debug():
                """デバッグ情報を更新"""
                return (
                    self.debugger.get_recent_logs(20),
                    self.debugger.get_tool_calls(10),
                    self.debugger.get_errors(10)
                )
            
            async def handle_refresh_tools():
                """利用可能なツール一覧を更新"""
                return self.available_tools if self.available_tools else []
            
            def handle_apply_settings(model: str, temp: float, top_p_val: float):
                """モデル設定を適用"""
                self.model_name = model
                self.model_params = {
                    "temperature": temp,
                    "top_p": top_p_val
                }
                
                if self.is_connected:
                    self.integration.set_model(model)
                    self.multimodal.set_model(model)
                    self.integration.set_model_parameters(self.model_params)
                
                return f"Settings applied: model={model}, temperature={temp}, top_p={top_p_val}"
            
            # イベントバインディング
            connect_btn.click(
                fn=handle_connect,
                outputs=[generated_response, status_md]
            )
            
            submit_btn.click(
                fn=handle_user_input,
                inputs=[text_input, image_input, response_style],
                outputs=[generated_response, history_display]
            )
            
            reset_btn.click(
                fn=reset_chat_history,
                inputs=[],
                outputs=[text_input, image_input, response_style, 
                        generated_response, history_display]
            )
            
            refresh_debug_btn.click(
                fn=handle_refresh_debug,
                outputs=[logs_json, tool_calls_json, errors_json]
            )
            
            refresh_tools_btn.click(
                fn=handle_refresh_tools,
                outputs=tools_json
            )
            
            apply_settings_btn.click(
                fn=handle_apply_settings,
                inputs=[model_select, temperature, top_p],
                outputs=generated_response
            )
            
            # 初期デバッグ情報の表示
            app.load(
                fn=handle_refresh_debug,
                outputs=[logs_json, tool_calls_json, errors_json]
            )
        
        return app
    
    def run(self, server_path: Optional[str] = None, port: int = 7860, share: bool = False) -> None:
        """
        アプリケーションを実行
        
        Args:
            server_path: MCPサーバーのパス（オプション）
            port: UIのポート番号
            share: 共有リンクを生成するかどうか
        """
        # サーバーパスが指定されている場合は接続
        if server_path:
            async def connect():
                await self.connect_to_server(server_path)
            asyncio.run(connect())
        
        app = self.build_ui()
        app.launch(server_port=port, share=share)

def main():
    """アプリケーションのコマンドラインエントリーポイント"""
    parser = argparse.ArgumentParser(description="Ollama MCP Client & Agent")
    parser.add_argument("--model", default="gemma3:27b", help="Ollama model name")
    parser.add_argument("--server", help="MCP server path or URL")
    parser.add_argument("--port", type=int, default=7860, help="Web UI port")
    parser.add_argument("--debug", default="info", 
                       help="Debug level (debug, info, warning, error)")
    parser.add_argument("--share", action="store_true", 
                       help="Generate a shareable link")
    
    args = parser.parse_args()
    
    app = OllamaMCPApp(model_name=args.model, debug_level=args.debug)
    app.run(server_path=args.server, port=args.port, share=args.share)

if __name__ == "__main__":
    main() 