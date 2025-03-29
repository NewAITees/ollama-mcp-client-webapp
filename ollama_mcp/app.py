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
    def __init__(self, model_name: str = "gemma3:4b", debug_level: str = "info", direct_mode: bool = False):
        """
        OllamaMCPAppを初期化
        
        Args:
            model_name: 使用するOllamaモデル名
            debug_level: デバッグログのレベル
            direct_mode: MCPサーバーを使用せず直接Ollamaと通信するかどうか
        """
        self.model_name = model_name
        self.debug_level = debug_level
        self.direct_mode = direct_mode
        
        self.client = ollama.Client()  # Ollama公式クライアント（APIチェック用）
        self.debugger = AgnoMCPDebugger(level=debug_level)
        self.integration = AgnoClient(
            model_name=model_name, 
            debug_level=debug_level,
            direct_mode=direct_mode
        )
        
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
                # 画像パスのリストを作成（存在する場合）
                image_paths = []
                
                # 一時ディレクトリを使用して画像を処理
                with tempfile.TemporaryDirectory() as temp_dir_str:
                    temp_dir = Path(temp_dir_str)
                    
                    # 画像がメッセージに含まれている場合
                    if 'images' in self.history[-1]:
                        for i, img_base64 in enumerate(self.history[-1]['images']):
                            img_data = ollama.utils.decode_image_base64(img_base64)
                            img_path = temp_dir / f"image_{i}.jpg"
                            with open(img_path, "wb") as f:
                                f.write(img_data)
                            image_paths.append(str(img_path))
                    
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