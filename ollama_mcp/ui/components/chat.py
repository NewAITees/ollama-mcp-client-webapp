"""
チャットインターフェースのコンポーネント
"""
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional

import gradio as gr

from ollama_mcp.client import OllamaMCPClient
from ollama_mcp.agent import OllamaMCPAgent

class ChatComponent:
    """
    チャットインターフェースのコンポーネント
    
    主な責務:
    - チャットUIの構築
    - メッセージの送受信
    - 画像アップロード機能
    """
    def __init__(self, client: OllamaMCPClient, agent: Optional[OllamaMCPAgent] = None):
        """
        ChatComponentを初期化
        
        Args:
            client: MCPクライアント
            agent: MCPエージェント（オプション）
        """
        self.client = client
        self.agent = agent
    
    def build(self) -> gr.Blocks:
        """
        チャットインターフェースを構築
        
        Returns:
            Gradio Blocksインスタンス
        """
        with gr.Blocks() as chat:
            chatbot = gr.Chatbot(height=500)
            
            with gr.Row():
                with gr.Column(scale=4):
                    message = gr.Textbox(
                        placeholder="メッセージを入力...",
                        label="メッセージ",
                        lines=2
                    )
                with gr.Column(scale=1):
                    image_upload = gr.File(
                        file_types=["image"],
                        file_count="multiple",
                        label="画像をアップロード"
                    )
            
            send_button = gr.Button("送信")
            
            def process_message(message: str, images, history: list) -> Tuple[list, None]:
                """
                メッセージと画像を処理
                
                Args:
                    message: ユーザーメッセージ
                    images: アップロードされた画像ファイル
                    history: 会話履歴
                    
                Returns:
                    更新された履歴とクリアされた画像アップロード
                """
                if not self.client.connected:
                    history.append((message, "サーバーに接続されていません。まず接続してください。"))
                    return history, None
                
                history.append((message, "..."))
                
                try:
                    # 画像の一時保存
                    image_paths = []
                    if images:
                        for i, img in enumerate(images):
                            if img is not None:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
                                    temp.write(img)
                                    image_paths.append(temp.name)
                    
                    # 画像があるかどうかでメソッドを分岐
                    if image_paths and self.agent:
                        response = self.agent.chat_with_images(message, image_paths)
                    elif image_paths:
                        response = self.client.chat_with_images(message, image_paths)
                    elif self.agent:
                        response = self.agent.run(message)
                    else:
                        response = self.client.process_query(message)
                    
                    history[-1] = (message, response)
                    
                    # 一時ファイルの削除
                    for path in image_paths:
                        try:
                            Path(path).unlink()
                        except Exception as e:
                            print(f"Failed to delete temp file: {e}")
                            
                except Exception as e:
                    print(f"処理エラー: {e}")
                    history[-1] = (message, f"エラーが発生しました: {str(e)}")
                
                return history, None
            
            send_button.click(
                fn=process_message,
                inputs=[message, image_upload, chatbot],
                outputs=[chatbot, image_upload]
            )
            
            message.submit(
                fn=process_message,
                inputs=[message, image_upload, chatbot],
                outputs=[chatbot, image_upload]
            )
        
        return chat 