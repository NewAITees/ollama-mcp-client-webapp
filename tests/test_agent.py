"""
OllamaMCPAgent のテストケース
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ollama_mcp.client import OllamaMCPClient
from ollama_mcp.agent import OllamaMCPAgent, AgentMemory, TaskPlanner

@pytest.mark.asyncio
async def test_agent_initialization():
    """エージェントの初期化テスト"""
    client = OllamaMCPClient()
    agent = OllamaMCPAgent(client)
    
    assert agent.client == client
    assert isinstance(agent.memory, AgentMemory)
    assert isinstance(agent.planner, TaskPlanner)

@pytest.mark.asyncio
async def test_agent_memory():
    """エージェントメモリのテスト"""
    memory = AgentMemory()
    
    # メッセージの追加テスト
    memory.add_message("user", "テストメッセージ")
    assert len(memory.messages) == 1
    assert memory.messages[0]["role"] == "user"
    assert memory.messages[0]["content"] == "テストメッセージ"
    
    # コンテキストの更新テスト
    memory.update_context("test_key", "test_value")
    context = memory.get_context()
    assert "test_key" in context
    assert context["test_key"] == "test_value"

@pytest.mark.asyncio
async def test_task_planner():
    """タスクプランナーのテスト"""
    planner = TaskPlanner()
    steps = await planner.create_plan("テストタスク")
    
    assert isinstance(steps, list)
    assert len(steps) > 0
    assert all(isinstance(step, str) for step in steps)

@pytest.mark.asyncio
async def test_agent_run():
    """エージェント実行のテスト"""
    client = OllamaMCPClient()
    client.process_query = AsyncMock(return_value="テスト応答")
    agent = OllamaMCPAgent(client)
    
    result = await agent.run("テストタスク")
    assert isinstance(result, str)
    assert len(result) > 0

@pytest.mark.asyncio
async def test_agent_plan_task():
    """タスク計画のテスト"""
    client = OllamaMCPClient()
    agent = OllamaMCPAgent(client)
    
    steps = await agent.plan_task("テストタスク")
    assert isinstance(steps, list)
    assert len(steps) > 0

@pytest.mark.asyncio
async def test_agent_execute_step():
    """ステップ実行のテスト"""
    client = OllamaMCPClient()
    client.process_query = AsyncMock(return_value="ステップ実行結果")
    agent = OllamaMCPAgent(client)
    
    result = await agent.execute_step("テストステップ")
    assert result == "ステップ実行結果"

@pytest.mark.asyncio
async def test_agent_reflect_on_result():
    """結果の反省テスト"""
    client = OllamaMCPClient()
    agent = OllamaMCPAgent(client)
    
    # エラーを含む結果の反省
    reflection = await agent.reflect_on_result("エラーが発生しました")
    assert isinstance(reflection, str)
    assert len(reflection) > 0
    
    # 正常な結果の反省
    reflection = await agent.reflect_on_result("正常に完了しました")
    assert reflection is None 