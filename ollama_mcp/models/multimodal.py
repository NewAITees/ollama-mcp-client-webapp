"""
マルチモーダル機能を持つOllamaモデル

主な責務:
- 画像とテキストの両方を処理
- 画像のエンコードと送信
- マルチモーダル応答の処理
"""

import base64
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
import aiohttp
from PIL import Image
import io

from ollama_mcp.models.ollama import OllamaModel

class MultimodalModel(OllamaModel):
    """
    マルチモーダル機能を持つOllamaモデル
    
    主な責務:
    - 画像とテキストの両方を処理
    - 画像のエンコードと送信
    - マルチモーダル応答の処理
    """
    def __init__(self, model_name: str = "gemma"):
        """
        MultimodalModelを初期化
        
        Args:
            model_name: モデル名（gemmaなどマルチモーダル対応モデル）
        """
        super().__init__(model_name)
        self.api_base = "http://localhost:11434/api"
    
    async def process_image(self, image_path: Union[str, Path]) -> str:
        """
        画像を処理してbase64エンコードされた文字列を返す
        
        Args:
            image_path: 画像ファイルのパス
            
        Returns:
            base64エンコードされた画像データ
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # 画像をバイナリで読み込み
        with open(image_path, "rb") as img_file:
            img_data = img_file.read()
            
        # base64エンコード
        base64_data = base64.b64encode(img_data).decode("utf-8")
        return base64_data
    
    async def generate_with_images(self, prompt: str, image_paths: List[Union[str, Path]]) -> str:
        """
        画像とテキストプロンプトを使用してテキストを生成
        
        Args:
            prompt: テキストプロンプト
            image_paths: 画像ファイルのパスのリスト
            
        Returns:
            生成されたテキスト
        """
        url = f"{self.api_base}/generate"
        
        # 画像の処理
        images = []
        for img_path in image_paths:
            image_data = await self.process_image(img_path)
            images.append({
                "data": image_data,
                "type": "image/jpeg"  # 他の形式にも対応可能
            })
        
        # リクエストペイロードの構築
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "images": images,
            **self.parameters
        }
        
        if self.context:
            payload["context"] = self.context
        
        # APIリクエスト
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, json=payload)
            await response.raise_for_status()
            result = await response.json()
            self.context = result.get("context", [])
            return result["response"]
    
    async def chat_with_images(self, message: str, image_paths: List[Union[str, Path]]) -> str:
        """
        画像を含むチャットメッセージを送信
        
        Args:
            message: ユーザーメッセージ
            image_paths: 画像ファイルのパスのリスト
            
        Returns:
            モデルの応答
        """
        url = f"{self.api_base}/chat"
        
        # 画像の処理
        images = []
        for img_path in image_paths:
            image_data = await self.process_image(img_path)
            images.append({
                "data": image_data,
                "type": "image/jpeg"  # 他の形式にも対応可能
            })
        
        # リクエストペイロードの構築
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": message,
                    "images": images
                }
            ],
            **self.parameters
        }
        
        # APIリクエスト
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, json=payload)
            await response.raise_for_status()
            result = await response.json()
            return result["message"]["content"] 