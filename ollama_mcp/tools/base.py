"""
MCP ツールの基底クラスと定義
"""
from typing import Dict, Any, Callable, TypeVar, Generic, Optional

T = TypeVar('T')

class Tool(Generic[T]):
    """
    MCP ツールを表現する基底クラス
    
    主な責務:
    - ツールの定義と説明
    - 入力スキーマの定義
    - 実行ロジックの提供
    """
    def __init__(self, name: str, description: str, input_schema: Dict[str, Any], func: Callable):
        """
        Toolを初期化
        
        Args:
            name: ツール名
            description: ツールの説明
            input_schema: 入力スキーマ
            func: 実行関数
        """
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.func = func
    
    @classmethod
    def register(cls, name: str, description: str, input_schema: Dict[str, Any]):
        """
        デコレータとしてツールを登録するファクトリーメソッド
        
        Args:
            name: ツール名
            description: ツールの説明
            input_schema: 入力スキーマ
            
        Returns:
            デコレータ関数
        """
        def decorator(func):
            return cls(name, description, input_schema, func)
        return decorator
    
    async def __call__(self, **kwargs) -> T:
        """
        ツールを実行
        
        Args:
            **kwargs: ツールへの引数
            
        Returns:
            ツールの実行結果
        """
        return await self.func(**kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        辞書形式に変換
        
        Returns:
            ツール定義の辞書
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        } 