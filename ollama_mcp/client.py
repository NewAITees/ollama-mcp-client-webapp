"""
MCPクライアントのコア実装
"""
import asyncio
import json
from typing import Dict, List, Optional, Any

from loguru import logger

from ollama_mcp.debug import DebugLogger
from ollama_mcp.tools.registry import ToolRegistry

class OllamaMCPClient:
    """
    MCPサーバーと連携するクライアントクラス
    
    主な責務:
    - MCPサーバーとの接続確立・維持
    - ツールの検出と登録
    - クエリ処理の調整
    - Ollamaモデルとの対話
    """
    def __init__(self, model_name: str = "llama3", debug_level: str = "info"):
        """
        OllamaMCPClientを初期化
        
        Args:
            model_name: 使用するOllamaモデル名
            debug_level: デバッグログのレベル
        """
        self.model_name = model_name
        self.debug_logger = DebugLogger(level=debug_level)
        self.tool_registry = ToolRegistry()
        self.connected = False
        self.server_info = None
        self._listeners = {}
        
        self.debug_logger.log(f"Initialized OllamaMCPClient with model {model_name}", "info")
    
    async def connect_to_server(self, server_path: str) -> List[Dict[str, Any]]:
        """
        MCPサーバーに接続し、使用可能なツールを取得
        
        Args:
            server_path: MCPサーバーのパスまたはURL
            
        Returns:
            利用可能なツールのリスト
        """
        self.debug_logger.log(f"Connecting to MCP server at {server_path}", "info")
        
        # 接続処理（ここは実際のMCP実装によります）
        # ...
        
        # 仮のツールリスト（実際の実装では、サーバーから取得します）
        tools = [
            {
                "name": "weather",
                "description": "Get weather information for a location",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name or location"}
                    },
                    "required": ["location"]
                }
            }
        ]
        
        # ツールの登録
        for tool in tools:
            self.tool_registry.register_tool(tool)
        
        self.connected = True
        self.server_info = {"path": server_path, "connected_at": "2025-03-22T12:00:00"}
        
        self.debug_logger.log(f"Connected to server {server_path}, found {len(tools)} tools", "info")
        return tools
    
    async def process_query(self, query: str) -> str:
        """
        ユーザークエリを処理
        
        Args:
            query: ユーザーからの入力テキスト
            
        Returns:
            応答テキスト
        """
        if not self.connected:
            raise RuntimeError("Not connected to an MCP server")
        
        self.debug_logger.log(f"Processing query: {query}", "info")
        
        # Ollamaモデルへの送信処理
        # ...
        
        # 仮の応答（実際の実装では、Ollamaモデルから取得します）
        response = f"応答: '{query}' に対する回答です。"
        
        self.debug_logger.log(f"Generated response", "info")
        return response
    
    async def close(self) -> None:
        """接続を閉じる"""
        if self.connected:
            # 接続クローズ処理
            # ...
            
            self.connected = False
            self.debug_logger.log("Connection closed", "info")
    
    def set_model(self, model_name: str) -> None:
        """モデルを設定"""
        self.model_name = model_name
        self.debug_logger.log(f"Model changed to {model_name}", "info")
    
    def set_model_parameters(self, params: Dict[str, Any]) -> None:
        """モデルパラメータを設定"""
        # パラメータ設定処理
        # ...
        
        self.debug_logger.log(f"Model parameters updated: {params}", "info")
    
    def on(self, event_name: str, callback):
        """イベントリスナーを登録"""
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback) 