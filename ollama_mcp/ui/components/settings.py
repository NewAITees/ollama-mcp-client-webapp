"""
設定インターフェースのコンポーネント
"""
from typing import Dict, List, Any, Optional, Tuple

import gradio as gr

from ollama_mcp.client import OllamaMCPClient
from ollama_mcp.models.ollama import OllamaModel

class SettingsComponent:
    """
    設定インターフェースのコンポーネント
    
    主な責務:
    - サーバー接続設定
    - モデル選択
    - パラメータ設定
    """
    def __init__(self, client: OllamaMCPClient):
        """
        SettingsComponentを初期化
        
        Args:
            client: MCPクライアント
        """
        self.client = client
    
    def build(self) -> gr.Blocks:
        """
        設定インターフェースを構築
        
        Returns:
            Gradio Blocksインスタンス
        """
        with gr.Blocks() as settings:
            with gr.Row():
                with gr.Column():
                    # サーバー接続設定
                    with gr.Row():
                        server_path = gr.Textbox(
                            placeholder="サーバーパスを入力...",
                            label="サーバーパス"
                        )
                        connect_button = gr.Button("接続")
                    
                    connection_status = gr.JSON(label="接続状態")
                    
                    def connect_to_server(server_path: str) -> Dict[str, Any]:
                        """
                        サーバーに接続
                        
                        Args:
                            server_path: サーバーパス
                            
                        Returns:
                            接続状態
                        """
                        try:
                            self.client.connect_to_server(server_path)
                            return {
                                "status": "success",
                                "message": f"サーバー {server_path} に接続しました。"
                            }
                        except Exception as e:
                            return {
                                "status": "error",
                                "message": f"接続エラー: {str(e)}"
                            }
                    
                    connect_button.click(
                        fn=connect_to_server,
                        inputs=[server_path],
                        outputs=[connection_status]
                    )
                
                with gr.Column():
                    # モデル設定
                    model_type = gr.Radio(
                        choices=["標準", "マルチモーダル"],
                        value="標準",
                        label="モデルタイプ"
                    )
                    
                    standard_model = gr.Dropdown(
                        choices=["llama3", "mistral", "phi"],
                        value=self.client.model_name,
                        label="標準モデル",
                        visible=True
                    )
                    
                    multimodal_model = gr.Dropdown(
                        choices=["gemma", "llava", "bakllava"],
                        label="マルチモーダルモデル",
                        visible=False
                    )
                    
                    update_model_button = gr.Button("モデルを更新")
                    
                    def toggle_model_selector(model_type: str) -> Tuple[gr.update, gr.update]:
                        """
                        モデルタイプによる表示切替
                        
                        Args:
                            model_type: モデルタイプ
                            
                        Returns:
                            標準モデルとマルチモーダルモデルの表示状態
                        """
                        return (
                            gr.update(visible=model_type == "標準"),
                            gr.update(visible=model_type == "マルチモーダル")
                        )
                    
                    model_type.change(
                        fn=toggle_model_selector,
                        inputs=[model_type],
                        outputs=[standard_model, multimodal_model]
                    )
                    
                    async def update_model(
                        model_type: str,
                        standard_model: str,
                        multimodal_model: str
                    ) -> Dict[str, Any]:
                        """
                        モデルを更新
                        
                        Args:
                            model_type: モデルタイプ
                            standard_model: 標準モデル名
                            multimodal_model: マルチモーダルモデル名
                            
                        Returns:
                            更新状態
                        """
                        selected_model = multimodal_model if model_type == "マルチモーダル" else standard_model
                        if not selected_model:
                            return {
                                "status": "error",
                                "message": "モデルが選択されていません。"
                            }
                        
                        if not self.client.connected:
                            return {
                                "status": "error",
                                "message": "クライアントが初期化されていません。"
                            }
                        
                        self.client.set_model(selected_model)
                        
                        return {
                            "status": "success",
                            "message": f"モデルを {selected_model} に更新しました。"
                        }
                    
                    update_model_button.click(
                        fn=update_model,
                        inputs=[model_type, standard_model, multimodal_model],
                        outputs=[connection_status]
                    )
                    
                    async def refresh_models(model_type: str) -> Tuple[List[str], List[str]]:
                        """
                        モデル一覧を更新
                        
                        Args:
                            model_type: モデルタイプ
                            
                        Returns:
                            標準モデルとマルチモーダルモデルのリスト
                        """
                        if not self.client.connected:
                            return (
                                ["llama3", "mistral", "phi"],
                                ["gemma", "llava", "bakllava"]
                            )
                        
                        try:
                            model = OllamaModel()
                            
                            all_models = await model.get_installed_models()
                            multimodal_models = await model.get_multimodal_models()
                            
                            standard_models = [m for m in all_models if m not in multimodal_models]
                            
                            return standard_models, multimodal_models
                        except Exception as e:
                            print(f"モデル一覧の取得に失敗: {e}")
                            return (
                                ["llama3", "mistral", "phi"],
                                ["gemma", "llava", "bakllava"]
                            )
                    
                    refresh_models_button = gr.Button("モデル一覧を更新")
                    
                    refresh_models_button.click(
                        fn=refresh_models,
                        inputs=[model_type],
                        outputs=[standard_model, multimodal_model]
                    )
        
        return settings 