"""
メインアプリケーションのエントリーポイント
"""
import argparse
import asyncio
import os
from typing import List, Optional, Dict, Any

from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.ui import AgentUI
from agno.tools.mcp import MCPTools

from ollama_mcp.agno_integration import OllamaMCPIntegration
from ollama_mcp.agno_multimodal import AgnoMultimodalIntegration
from ollama_mcp.debug_module import AgnoMCPDebugger

class OllamaMCPApp:
    """
    Ollama MCP Client & Agent のメインアプリケーション
    
    主な責務:
    - Agnoエージェントとツールの初期化
    - AgentUIの設定と起動
    - デバッグ機能の提供
    """
    def __init__(self, model_name: str = "llama3", debug_level: str = "info"):
        """
        OllamaMCPAppを初期化
        
        Args:
            model_name: 使用するOllamaモデル名
            debug_level: デバッグログのレベル
        """
        self.model_name = model_name
        self.debug_level = debug_level
        self.debugger = AgnoMCPDebugger(level=debug_level)
        self.integration = OllamaMCPIntegration(model_name=model_name, debug_level=debug_level)
        self.multimodal = AgnoMultimodalIntegration(model_name=model_name, debug_level=debug_level)
        self.agent = None
        self.mcp_tools = None
        
        self.debugger.log(f"OllamaMCPApp initialized with model {model_name}", "info")
    
    async def setup_agent(self, server_path: Optional[str] = None) -> Agent:
        """
        エージェントのセットアップ
        
        Args:
            server_path: MCPサーバーのパス（指定がなければ未接続状態で開始）
            
        Returns:
            セットアップされたエージェント
        """
        # Ollamaモデルの設定
        ollama_model = Ollama(
            id=self.model_name,
            name="Ollama",
            provider="Ollama",
            supports_multimodal=True
        )
        
        # MCPツールの初期化（サーバーパスが指定されている場合）
        tools = []
        if server_path:
            try:
                self.debugger.log(f"Connecting to MCP server at {server_path}", "info")
                tools = await self.integration.connect_to_server(server_path)
                self.mcp_tools = tools
                self.debugger.log(f"Connected to MCP server with {len(tools)} tools", "info")
            except Exception as e:
                self.debugger.record_error("connection_error", f"Failed to connect to server: {str(e)}")
                self.debugger.log(f"Starting without MCP server connection due to error: {str(e)}", "warning")
        
        # エージェントの初期化
        self.agent = Agent(
            model=ollama_model,
            tools=tools,
            description="Ollama MCP Client & Agent - An intelligent assistant powered by Ollama",
            instructions="You are an AI assistant that can use various tools to help the user. Respond in a helpful and concise manner.",
            markdown=True,
            show_tool_calls=True
        )
        
        return self.agent
    
    def run(self, server_path: Optional[str] = None, port: int = 7860, share: bool = False) -> None:
        """
        アプリケーションを実行
        
        Args:
            server_path: MCPサーバーのパス（オプション）
            port: UIのポート番号
            share: 共有リンクを生成するかどうか
        """
        async def _setup_and_run():
            agent = await self.setup_agent(server_path)
            ui = AgentUI(
                agents=[agent], 
                title="Ollama MCP Client & Agent",
                description="Powered by Ollama and Agno framework."
            )
            ui.run(port=port, share=share)
        
        # asyncioのイベントループを取得して実行
        try:
            asyncio.run(_setup_and_run())
        except KeyboardInterrupt:
            self.debugger.log("Application terminated by user", "info")
        except Exception as e:
            self.debugger.record_error("runtime_error", f"Application error: {str(e)}")
            raise

def main():
    """アプリケーションのコマンドラインエントリーポイント"""
    parser = argparse.ArgumentParser(description="Ollama MCP Client & Agent")
    parser.add_argument("--model", default="gemma3", help="Ollama model name")
    parser.add_argument("--server", help="MCP server path or URL")
    parser.add_argument("--port", type=int, default=7860, help="Web UI port")
    parser.add_argument("--debug", default="info", help="Debug level (debug, info, warning, error)")
    parser.add_argument("--share", action="store_true", help="Generate a shareable link")
    
    args = parser.parse_args()
    
    app = OllamaMCPApp(model_name=args.model, debug_level=args.debug)
    app.run(server_path=args.server, port=args.port, share=args.share)

if __name__ == "__main__":
    main() 