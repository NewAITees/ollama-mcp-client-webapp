"""
Agnoを使用したMCPサーバー統合モジュール
"""
import asyncio
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable

from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.tools.mcp import MCPTools
from agno.media import Image as AgnoImage
from mcp import StdioServerParameters

from .debug_module import AgnoMCPDebugger

class OllamaMCPIntegration:
    """
    MCPサーバーと連携するAgnoベースのクライアント
    
    主な責務:
    - MCPサーバーとの接続確立・維持
    - Agnoエージェントの設定
    - クエリ処理の調整
    - マルチモーダル機能の提供
    """
    def __init__(self, model_name: str = "llama2", debug_level: str = "info"):
        """
        OllamaMCPIntegrationを初期化
        
        Args:
            model_name: 使用するOllamaモデル名
            debug_level: デバッグログのレベル
        """
        self.model_name = model_name
        self.debug_level = debug_level
        self.server_parameters = None
        self.agent = None
        self.mcp_tools = None
        self.connected = False
        self.server_info = None
        self.debugger = AgnoMCPDebugger(level=debug_level)
        
        self.debugger.log(f"Initialized OllamaMCPIntegration with model {model_name}", "info")
        
    async def connect_to_server(self, server_path: str) -> List[Dict[str, Any]]:
        """
        MCPサーバーに接続し、使用可能なツールを取得
        
        Args:
            server_path: MCPサーバーのパスまたはURL
            
        Returns:
            利用可能なツールのリスト
        """
        self.debugger.log(f"Connecting to MCP server at {server_path}")
        
        try:
            # サーバーパラメータの設定
            self.server_parameters = StdioServerParameters(
                command=server_path,
                env={"PATH": "/usr/local/bin"}
            )
            
            # MCPツールの初期化
            self.mcp_tools = await MCPTools(server_params=self.server_parameters).__aenter__()
            
            # 利用可能なツールを取得
            tools = self.mcp_tools.mcp_resources
            
            # エージェントのセットアップ
            await self.setup_agent(tools)
            
            self.connected = True
            self.debugger.log(f"Connected to MCP server at {server_path}")
            
            return tools
            
        except Exception as e:
            self.debugger.record_error(
                "connection_error",
                f"Error connecting to MCP server: {str(e)}"
            )
            raise
    
    async def setup_agent(self, tools: List[Dict[str, Any]]) -> None:
        """エージェントのセットアップ
        
        Args:
            tools: 利用可能なツールのリスト
        """
        try:
            # エージェントの初期化
            self.agent = Agent(
                model=self.model_name,
                tools=tools,
                show_tool_calls=True
            )
            
            self.debugger.log(f"Agent setup completed with {len(tools)} tools")
            
        except Exception as e:
            self.debugger.record_error(
                "agent_setup_error",
                f"Error setting up agent: {str(e)}"
            )
            raise
    
    async def process_query(self, query: str) -> str:
        """
        ユーザークエリを処理
        
        Args:
            query: ユーザーからの入力テキスト
            
        Returns:
            応答テキスト
        """
        if not self.connected or not self.agent:
            raise RuntimeError("Not connected to an MCP server")
        
        self.debugger.log(f"Processing query: {query}")
        
        try:
            response = await self.agent.arun(query)
            return response.response
        except Exception as e:
            self.debugger.record_error(
                "query_error",
                f"Error processing query: {str(e)}"
            )
            raise
    
    async def process_multimodal_query(self, query: str, image_paths: List[Union[str, Path]]) -> str:
        """
        画像を含むクエリを処理
        
        Args:
            query: ユーザーからの入力テキスト
            image_paths: 画像ファイルのパスのリスト
            
        Returns:
            応答テキスト
        """
        if not self.connected or not self.agent:
            raise RuntimeError("Not connected to an MCP server")
        
        self.debugger.log(f"Processing multimodal query with {len(image_paths)} images")
        
        try:
            # 画像をAgnoイメージに変換
            images = []
            for img_path in image_paths:
                img_path = Path(img_path)
                if img_path.exists():
                    images.append(AgnoImage(filepath=str(img_path)))
                else:
                    self.debugger.record_error(
                        "image_not_found",
                        f"Image file not found: {img_path}"
                    )
            
            # マルチモーダルクエリを処理
            response = await self.agent.arun(query, images=images)
            return response.response
        except Exception as e:
            self.debugger.record_error(
                "multimodal_processing_error",
                f"Error processing multimodal query: {str(e)}"
            )
            raise
    
    async def stream_query(self, query: str, callback: Optional[Callable[[str], None]] = None) -> str:
        """
        ストリーミングクエリを処理
        
        Args:
            query: ユーザーからの入力テキスト
            callback: ストリーミング応答を処理するコールバック関数
            
        Returns:
            応答テキスト全体
        """
        if not self.connected or not self.agent:
            raise RuntimeError("Not connected to an MCP server")
        
        self.debugger.log(f"Processing streaming query: {query}")
        
        try:
            full_response = []
            
            async for response_chunk in self.agent.astream(query):
                chunk_text = response_chunk.response
                full_response.append(chunk_text)
                
                if callback:
                    await callback(chunk_text)
                
                self.debugger.log(f"Received chunk: {chunk_text}", "debug")
            
            return "".join(full_response)
        except Exception as e:
            self.debugger.record_error(
                "streaming_error",
                f"Error processing streaming query: {str(e)}"
            )
            raise
    
    async def close(self) -> None:
        """接続を閉じる"""
        if self.mcp_tools:
            await self.mcp_tools.__aexit__(None, None, None)
        
        self.connected = False
        self.agent = None
        self.mcp_tools = None
        self.debugger.log("Closed MCP connection")
    
    def set_model(self, model_name: str) -> None:
        """モデルを設定"""
        self.model_name = model_name
        
        # 既に接続済みの場合は再接続が必要
        if self.connected:
            self.debugger.log(f"Model changed to {model_name}, reconnection required", "info")
        else:
            self.debugger.log(f"Model changed to {model_name}", "info")
    
    def set_model_parameters(self, params: Dict[str, Any]) -> None:
        """モデルパラメータを設定"""
        if self.agent and hasattr(self.agent.model, 'parameters'):
            for key, value in params.items():
                self.agent.model.parameters[key] = value
            self.debugger.log(f"Model parameters updated: {params}", "info") 