"""
メインアプリケーションのエントリーポイント
"""
import gradio as gr

from ollama_mcp.client import OllamaMCPClient
from ollama_mcp.agent import OllamaMCPAgent
from ollama_mcp.ui.components.chat import ChatComponent
from ollama_mcp.ui.components.settings import SettingsComponent

class OllamaMCPApp:
    """
    Ollama MCP Client & Agentのメインアプリケーション
    
    主な責務:
    - UIコンポーネントの統合
    - クライアントとエージェントの管理
    - アプリケーションの起動と停止
    """
    def __init__(self, model_name: str = "llama3", debug_level: str = "info"):
        """
        OllamaMCPAppを初期化
        
        Args:
            model_name: 使用するOllamaモデル名
            debug_level: デバッグログのレベル
        """
        self.client = OllamaMCPClient(model_name=model_name, debug_level=debug_level)
        self.agent = OllamaMCPAgent(client=self.client)
        
        self.chat_component = ChatComponent(client=self.client, agent=self.agent)
        self.settings_component = SettingsComponent(client=self.client)
    
    def build_ui(self) -> gr.Blocks:
        """
        アプリケーションのUIを構築
        
        Returns:
            Gradio Blocksインスタンス
        """
        with gr.Blocks(title="Ollama MCP Client & Agent") as app:
            gr.Markdown("# Ollama MCP Client & Agent")
            
            with gr.Tabs():
                with gr.Tab("チャット"):
                    self.chat_component.build()
                
                with gr.Tab("設定"):
                    self.settings_component.build()
            
            # フッター
            gr.Markdown("Ollama MCP Client & Agent © 2025")
        
        return app
    
    def run(self, port: int = 7860, share: bool = False) -> None:
        """
        アプリケーションを実行
        
        Args:
            port: 使用するポート番号
            share: Gradio共有リンクを生成するかどうか
        """
        app = self.build_ui()
        app.launch(server_port=port, share=share)

def main():
    """アプリケーションのエントリーポイント"""
    app = OllamaMCPApp()
    app.run()

if __name__ == "__main__":
    main() 