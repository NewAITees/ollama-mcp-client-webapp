"""
Agnoフレームワークを活用した統合MCPクライアント
"""
import asyncio
import os
import json
import aiohttp
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable

from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.tools.mcp import MCPTools
from agno.media import Image as AgnoImage
from mcp import StdioServerParameters

from ollama_mcp.debug_module import AgnoMCPDebugger

class AgnoClient:
    """
    Agnoベースの統合クライアント
    
    主な責務:
    - MCPサーバー接続と管理
    - Ollamaモデルとの直接/間接通信
    - マルチモーダル処理
    """
    def __init__(
        self, 
        model_name: str = "llama3", 
        debug_level: str = "info",
        direct_mode: bool = False,
        base_url: str = "http://localhost:11434"
    ):
        """
        統合クライアントの初期化
        
        Args:
            model_name: 使用するモデル名
            debug_level: デバッグレベル
            direct_mode: Ollamaと直接通信するかどうか
            base_url: Ollama API の URL（direct_mode=True の場合）
        """
        self.model_name = model_name
        self.debug_level = debug_level
        self.direct_mode = direct_mode
        self.base_url = base_url
        
        self.debugger = AgnoMCPDebugger(level=debug_level)
        self.agent = None
        self.mcp_tools = None
        self.connected = False
        self.server_info = None
        
        # モデルパラメータ
        self.model_params = {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 2000
        }
        
        self.debugger.log(f"Initialized AgnoClient with model {model_name}", "info")
    
    async def connect_to_server(self, server_path: str) -> List[Dict[str, Any]]:
        """
        MCPサーバーに接続し、使用可能なツールを取得
        
        Args:
            server_path: MCPサーバーのパスまたはURL
            
        Returns:
            利用可能なツールのリスト
        """
        if self.direct_mode:
            self.debugger.log("Direct mode enabled, not connecting to MCP server", "info")
            # direct_modeの場合はエージェントだけ設定
            await self.setup_agent()
            self.connected = True
            return []
        
        self.debugger.log(f"Connecting to MCP server at {server_path}", "info")
        
        try:
            # サーバーパラメータの設定
            self.server_parameters = StdioServerParameters(
                command=server_path,
                env={"PATH": os.environ.get("PATH", "/usr/local/bin")}
            )
            
            # MCPツールの初期化
            self.mcp_tools = await MCPTools(server_params=self.server_parameters).__aenter__()
            
            # 利用可能なツールを取得
            tools = self.mcp_tools.mcp_resources
            
            # エージェントのセットアップ
            await self.setup_agent(tools)
            
            self.connected = True
            self.server_info = {
                "path": server_path,
                "connected_at": asyncio.get_event_loop().time(),
                "tools_count": len(tools)
            }
            
            self.debugger.log(f"Connected to MCP server with {len(tools)} tools available", "info")
            
            return tools
            
        except Exception as e:
            self.debugger.record_error(
                "connection_error",
                f"Error connecting to MCP server: {str(e)}"
            )
            raise
    
    async def setup_agent(self, tools: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        エージェントをセットアップ
        
        Args:
            tools: 利用可能なツールのリスト（None の場合は空リスト）
        """
        try:
            # None の場合は空リストに
            tools = tools or []
            

            from agno.tools.duckduckgo import DuckDuckGoTools
            
            # エージェントの初期化
            self.agent = Agent(
            model=Ollama(id=self.model_name),
           # tools=[DuckDuckGoTools()],
            markdown=True
            )
            
            self.debugger.log(f"Agent setup completed with {len(tools)} tools", "info")
            
        except Exception as e:
            self.debugger.record_error(
                "agent_setup_error",
                f"Error setting up agent: {str(e)}"
            )
            raise
    
    async def process_query(
        self, 
        query: str,
        images: Optional[List[Union[str, Path]]] = None,
        stream: bool = False,
        callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        テキストまたはマルチモーダルクエリを処理
        
        Args:
            query: ユーザーからの入力テキスト
            images: 画像ファイルのパスのリスト（オプション）
            stream: ストリーミング応答を使用するかどうか
            callback: ストリーミング時に呼び出すコールバック関数
            
        Returns:
            応答テキスト
        """
        if not self.connected:
            if self.direct_mode:
                # 直接モードの場合、エージェントを設定
                await self.setup_agent()
                self.connected = True
            else:
                raise RuntimeError("Not connected to MCP server. Call connect_to_server first.")
        
        if not self.agent:
            await self.setup_agent()
        
        # リクエストをログに記録
        log_data = {"query": query}
        if images:
            log_data["images_count"] = len(images)
        self.debugger.log(f"Processing query with {log_data}", "info")
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # マルチモーダル入力の処理
            agno_images = []
            if images:
                for img_path in images:
                    img_path = Path(img_path)
                    if img_path.exists():
                        self.debugger.log(f"Adding image: {img_path}", "debug")
                        image = AgnoImage(filepath=str(img_path))
                        agno_images.append(image)
                    else:
                        error_msg = f"Image file not found: {img_path}"
                        self.debugger.record_error("image_not_found", error_msg)
                        raise FileNotFoundError(error_msg)
            
            # ストリーミング処理
            if stream:
                full_response = []
                
                self.debugger.log(f"Starting streaming response", "debug")
                async for response_chunk in self.agent.astream(query, images=agno_images or None):
                    chunk_text = response_chunk.content  # .response から .content に変更
                    full_response.append(chunk_text)
                    
                    if callback:
                        await callback(chunk_text)
                    
                    self.debugger.log(f"Received chunk: {chunk_text[:50]}...", "debug")
                
                result = "".join(full_response)
            else:
                # 通常の処理
                response = await self.agent.arun(query, images=agno_images or None)
                result = response.content  # .response から .content に変更
            
            # 処理時間を計測
            duration = asyncio.get_event_loop().time() - start_time
            self.debugger.log(f"Query processed in {duration:.2f}s", "info")
            
            return result
            
        except FileNotFoundError as e:
            self.debugger.record_error("file_not_found_error", str(e))
            raise
        except asyncio.TimeoutError as e:
            self.debugger.record_error("timeout_error", f"Query processing timed out: {str(e)}")
            raise
        except Exception as e:
            self.debugger.record_error("query_processing_error", f"Error processing query: {str(e)}")
            raise
        
    async def get_available_models(self) -> List[str]:
        """
        利用可能なモデルを取得
        
        Returns:
            モデル名のリスト
        """
        try:
            base_url = self.integration.base_url if hasattr(self.integration, 'base_url') else "http://localhost:11434"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        
                        # すべてのモデル名をリストとして返す
                        model_names = [model["name"] for model in models]
                        self.debugger.log(f"Retrieved {len(model_names)} models from API", "info")
                        return model_names
                    else:
                        self.debugger.record_error(
                            "model_fetch_error",
                            f"Failed to fetch models: HTTP {response.status}"
                        )
        except Exception as e:
            self.debugger.record_error(
                "model_fetch_error", 
                f"Error fetching available models: {str(e)}"
            )
        
        # API呼び出しが失敗した場合はデフォルト値を返す
        default_models = ["gemma3:27b", "llama3", "mistral", "mixtral"]
        self.debugger.log(f"Using default model list: {default_models}", "warning")
        return default_models
    
    def set_model(self, model_name: str) -> None:
        """
        使用するモデルを変更
        
        Args:
            model_name: 新しいモデル名
        """
        self.model_name = model_name
        self.debugger.log(f"Model changed to {model_name}", "info")
        
        # エージェントが既に存在する場合は設定を更新
        if self.agent and hasattr(self.agent, 'model'):
            self.agent.model.id = model_name
            self.debugger.log("Agent model updated", "debug")
    
    def set_model_parameters(self, params: Dict[str, Any]) -> None:
        """
        モデルパラメータを設定
        
        Args:
            params: パラメータ辞書
        """
        self.model_params.update(params)
        
        # エージェントが既に存在する場合は設定を更新
        if self.agent and hasattr(self.agent, 'model'):
            for key, value in params.items():
                # 属性が存在する場合のみ更新
                if hasattr(self.agent.model, key):
                    setattr(self.agent.model, key, value)
                else:
                    self.debugger.log(f"Warning: Model attribute {key} not found for update", "warning")
            
            self.debugger.log(f"Model parameters updated: {params}", "info")
    
    async def close(self) -> None:
        """接続を閉じる"""
        if self.mcp_tools:
            try:
                await self.mcp_tools.__aexit__(None, None, None)
                self.debugger.log("MCP tools connection closed", "info")
            except Exception as e:
                self.debugger.record_error("close_error", f"Error closing MCP tools: {str(e)}")
        
        self.connected = False
        self.agent = None
        self.mcp_tools = None
        self.debugger.log("Client resources released", "info")