"""
Ollamaモデルの基本実装
"""
import json
from typing import Dict, List, Any, Optional

import aiohttp

class OllamaModel:
    """
    Ollamaモデルの基本クラス
    
    主な責務:
    - Ollamaモデルとの通信
    - モデルパラメータの管理
    - コンテキストの管理
    """
    def __init__(self, model_name: str = "llama3"):
        """
        OllamaModelを初期化
        
        Args:
            model_name: モデル名
        """
        self.model_name = model_name
        self.api_base = "http://localhost:11434/api"
        self.parameters = {}
        self.context = None
    
    async def get_installed_models(self) -> List[str]:
        """
        インストール済みのモデル一覧を取得
        
        Returns:
            モデル名のリスト
        """
        url = f"{self.api_base}/tags"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                result = await response.json()
                
                return [model["name"] for model in result.get("models", [])]
    
    async def get_multimodal_models(self) -> List[str]:
        """
        マルチモーダル対応のOllamaモデルのリストを取得
        
        Returns:
            マルチモーダル対応モデル名のリスト
        """
        url = f"{self.api_base}/tags"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                result = await response.json()
                
                # マルチモーダル対応モデルのフィルタリング
                multimodal_models = []
                for model in result.get("models", []):
                    model_name = model.get("name", "")
                    # 現状ではgemma, llava, bakllavaなどがマルチモーダル対応
                    if any(mm in model_name.lower() for mm in ["gemma", "llava", "bakllava", "vision", "multimodal"]):
                        multimodal_models.append(model_name)
                
                return multimodal_models
    
    def set_parameters(self, params: Dict[str, Any]) -> None:
        """
        モデルパラメータを設定
        
        Args:
            params: パラメータ辞書
        """
        self.parameters = params
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        現在のモデルパラメータを取得
        
        Returns:
            パラメータ辞書
        """
        return self.parameters
    
    def set_context(self, context: Any) -> None:
        """
        コンテキストを設定
        
        Args:
            context: コンテキストデータ
        """
        self.context = context
    
    def get_context(self) -> Optional[Any]:
        """
        現在のコンテキストを取得
        
        Returns:
            コンテキストデータ
        """
        return self.context 