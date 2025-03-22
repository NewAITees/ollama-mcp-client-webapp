"""
高度なエージェント機能を提供する拡張フレームワーク
"""
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from ollama_mcp.client import OllamaMCPClient

class AgentMemory:
    """
    エージェントのメモリと状態を管理
    """
    def __init__(self):
        """AgentMemoryを初期化"""
        self.messages = []
        self.context = {}
        self.state = {}
    
    def add_message(self, role: str, content: str) -> None:
        """
        メッセージを追加
        
        Args:
            role: メッセージの送信者役割 (user, assistant)
            content: メッセージ内容
        """
        self.messages.append({"role": role, "content": content})
    
    def get_context(self) -> Dict[str, Any]:
        """
        現在のコンテキストを取得
        
        Returns:
            コンテキスト辞書
        """
        return self.context
    
    def update_context(self, key: str, value: Any) -> None:
        """
        コンテキストを更新
        
        Args:
            key: コンテキストキー
            value: コンテキスト値
        """
        self.context[key] = value

class TaskPlanner:
    """
    タスクの計画と実行を管理
    """
    def __init__(self):
        """TaskPlannerを初期化"""
        self.plans = []
    
    async def create_plan(self, task: str) -> List[str]:
        """
        タスクの計画を作成
        
        Args:
            task: 計画するタスク
            
        Returns:
            タスクステップのリスト
        """
        # タスク分解の実装
        # ...
        
        # 仮の計画（実際の実装では、LLMを使用して生成）
        steps = [
            f"ステップ1: {task}の情報を収集",
            f"ステップ2: 収集した情報を分析",
            f"ステップ3: 分析結果に基づいて行動"
        ]
        
        self.plans.append(steps)
        return steps

class OllamaMCPAgent:
    """
    MCPクライアントを拡張して高度なエージェント機能を提供
    
    主な責務:
    - タスクの計画と実行
    - コンテキストと状態の管理
    - 自律的な問題解決
    """
    def __init__(self, client: OllamaMCPClient, memory_enabled: bool = True, planning_enabled: bool = True):
        """
        OllamaMCPAgentを初期化
        
        Args:
            client: MCPクライアント
            memory_enabled: メモリを有効にするかどうか
            planning_enabled: 計画機能を有効にするかどうか
        """
        self.client = client
        self.memory = AgentMemory() if memory_enabled else None
        self.planner = TaskPlanner() if planning_enabled else None
    
    async def run(self, task: str) -> str:
        """
        タスクを実行
        
        Args:
            task: 実行するタスク
            
        Returns:
            タスク実行の結果
        """
        if self.memory:
            self.memory.add_message("user", task)
        
        if self.planner:
            steps = await self.planner.create_plan(task)
            results = []
            
            for step in steps:
                step_result = await self.execute_step(step)
                results.append(step_result)
                
                # 結果の反省
                reflection = await self.reflect_on_result(step_result)
                if reflection:
                    results.append(f"反省: {reflection}")
            
            final_result = "\n".join(results)
        else:
            # 計画なしで直接実行
            final_result = await self.client.process_query(task)
        
        if self.memory:
            self.memory.add_message("assistant", final_result)
        
        return final_result
    
    async def plan_task(self, task: str) -> List[str]:
        """
        タスクの計画のみを取得
        
        Args:
            task: 計画するタスク
            
        Returns:
            タスクステップのリスト
        """
        if not self.planner:
            raise RuntimeError("Planning is not enabled")
        
        return await self.planner.create_plan(task)
    
    async def execute_step(self, step: str) -> str:
        """
        特定のステップを実行
        
        Args:
            step: 実行するステップ
            
        Returns:
            ステップ実行の結果
        """
        return await self.client.process_query(step)
    
    async def reflect_on_result(self, result: str) -> Optional[str]:
        """
        結果について反省
        
        Args:
            result: 反省する結果
            
        Returns:
            反省のテキスト、必要ない場合はNone
        """
        # 反省の実装
        # ...
        
        # 仮の反省（実際の実装では、LLMを使用して生成）
        if "エラー" in result or "失敗" in result:
            return "失敗の原因を分析し、次回は異なるアプローチを試みる必要があります。"
        
        return None

    async def run_with_images(self, task: str, image_paths: List[Union[str, Path]]) -> str:
        """
        画像を含むタスクを実行
        
        Args:
            task: 実行するタスク
            image_paths: 画像ファイルのパスのリスト
            
        Returns:
            タスク実行の結果
        """
        if self.memory:
            self.memory.add_message("user", task)
        
        if self.planner:
            # タスクの計画（画像は計画段階では使用しない）
            steps = await self.planner.create_plan(task)
            results = []
            
            # 各ステップで画像を使用
            for step in steps:
                step_result = await self.execute_step_with_images(step, image_paths)
                results.append(step_result)
                
                # 結果の反省
                reflection = await self.reflect_on_result(step_result)
                if reflection:
                    results.append(f"反省: {reflection}")
            
            final_result = "\n".join(results)
        else:
            # 計画なしで直接実行
            final_result = await self.client.process_multimodal_query(task, image_paths)
        
        if self.memory:
            self.memory.add_message("assistant", final_result)
        
        return final_result

    async def execute_step_with_images(self, step: str, image_paths: List[Union[str, Path]]) -> str:
        """
        画像を含む特定のステップを実行
        
        Args:
            step: 実行するステップ
            image_paths: 画像ファイルのパスのリスト
            
        Returns:
            ステップ実行の結果
        """
        return await self.client.process_multimodal_query(step, image_paths)

    async def chat_with_images(self, message: str, image_paths: List[Union[str, Path]]) -> str:
        """
        画像を含むチャットメッセージを送信
        
        Args:
            message: ユーザーメッセージ
            image_paths: 画像ファイルのパスのリスト
            
        Returns:
            モデルの応答
        """
        if self.memory:
            self.memory.add_message("user", message)
        
        response = await self.client.chat_with_images(message, image_paths)
        
        if self.memory:
            self.memory.add_message("assistant", response)
        
        return response 