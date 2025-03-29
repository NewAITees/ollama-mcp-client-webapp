"""
Ollamaとの直接通信を行うモジュール
"""
import json
import aiohttp
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

class OllamaDirectClient:
    """
    Ollamaと直接通信を行うクライアント
    
    主な責務:
    - Ollamaとの直接通信
    - テキストチャット機能
    - マルチモーダル機能
    """
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "gemma:7b"):
        """
        OllamaDirectClientを初期化
        
        Args:
            base_url: OllamaサーバーのベースURL
            model_name: 使用するモデル名
        """
        self.base_url = base_url
        self.model_name = model_name
        self.model_params = {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 2000
        }
    
    async def chat(self, message: str) -> str:
        """
        テキストチャットを実行
        
        Args:
            message: ユーザーメッセージ
            
        Returns:
            モデルの応答
        """
        async with aiohttp.ClientSession() as session:
            data = {
                "model": self.model_name,
                "prompt": message,
                **self.model_params
            }
            
            try:
                full_response = []
                async with session.post(f"{self.base_url}/api/generate", json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error: {error_text}")
                    
                    # ストリーミングレスポンスを処理
                    async for line in response.content:
                        if not line:
                            continue
                        
                        try:
                            json_line = json.loads(line)
                            if "response" in json_line:
                                full_response.append(json_line["response"])
                            if json_line.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
                
                return "".join(full_response)
                
            except Exception as e:
                raise Exception(f"Failed to communicate with Ollama: {str(e)}")
    
    async def chat_with_images(self, message: str, image_paths: List[Union[str, Path]]) -> str:
        """
        画像を含むチャットを実行
        
        Args:
            message: ユーザーメッセージ
            image_paths: 画像ファイルのパスのリスト
            
        Returns:
            モデルの応答
        """
        # 画像をbase64エンコード
        images = []
        for img_path in image_paths:
            img_path = Path(img_path)
            if not img_path.exists():
                raise FileNotFoundError(f"Image not found: {img_path}")
            
            with open(img_path, "rb") as f:
                import base64
                image_data = base64.b64encode(f.read()).decode()
                images.append(image_data)
        
        async with aiohttp.ClientSession() as session:
            data = {
                "model": self.model_name,
                "prompt": message,
                "images": images,
                **self.model_params
            }
            
            try:
                full_response = []
                async with session.post(f"{self.base_url}/api/generate", json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error: {error_text}")
                    
                    # ストリーミングレスポンスを処理
                    async for line in response.content:
                        if not line:
                            continue
                        
                        try:
                            json_line = json.loads(line)
                            if "response" in json_line:
                                full_response.append(json_line["response"])
                            if json_line.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
                
                return "".join(full_response)
                
            except Exception as e:
                raise Exception(f"Failed to communicate with Ollama: {str(e)}")
    
    async def get_available_models(self) -> Dict[str, List[str]]:
        """
        利用可能なモデルの一覧を取得
        
        Returns:
            モデルタイプごとのモデル名のリスト
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get("models", [])
                    
                    return {
                        "text_models": [m["name"] for m in models if m.get("type") == "text"],
                        "multimodal_models": [m["name"] for m in models if m.get("type") == "multimodal"]
                    }
                else:
                    error_data = await response.text()
                    raise Exception(f"Failed to fetch models: {error_data}")
    
    def set_model(self, model_name: str) -> None:
        """
        使用するモデルを変更
        
        Args:
            model_name: 新しいモデル名
        """
        self.model_name = model_name
    
    def set_model_parameters(self, params: Dict[str, Any]) -> None:
        """
        モデルパラメータを設定
        
        Args:
            params: パラメータ辞書
        """
        self.model_params.update(params) 