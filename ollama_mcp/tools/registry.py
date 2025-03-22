"""
ツールの登録と管理を担当するレジストリ
"""
from typing import Dict, List, Optional, Any

class ToolRegistry:
    """
    ツールを管理するレジストリ
    
    主な責務:
    - ツールの登録と取得
    - スキーマの検証
    - ツールの一覧管理
    """
    def __init__(self):
        """ToolRegistryを初期化"""
        self._tools = {}
    
    def register_tool(self, tool: Dict[str, Any]) -> None:
        """
        ツールを登録
        
        Args:
            tool: ツール定義
        """
        tool_name = tool["name"]
        self._tools[tool_name] = tool
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """
        名前でツールを取得
        
        Args:
            name: ツール名
            
        Returns:
            ツール定義、見つからない場合はNone
        """
        return self._tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        利用可能なツールのリストを取得
        
        Returns:
            ツールのリスト
        """
        return list(self._tools.values())
    
    def get_tools_as_json(self) -> List[Dict[str, Any]]:
        """
        ツールをJSON形式で取得
        
        Returns:
            JSON形式のツールリスト
        """
        return self.list_tools()
    
    def validate_tool_call(self, name: str, args: Dict[str, Any]) -> bool:
        """
        ツールコールの引数を検証
        
        Args:
            name: ツール名
            args: 引数
            
        Returns:
            検証結果
        """
        tool = self.get_tool(name)
        if not tool:
            return False
        
        # スキーマの検証処理
        # ...
        
        return True 