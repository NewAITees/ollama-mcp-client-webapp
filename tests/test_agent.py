"""
OllamaMCPAgent のテストケース
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from ollama_mcp.client import OllamaMCPClient
from ollama_mcp.agent import OllamaMCPAgent, AgentMemory, TaskPlanner

# テスト用の画像パス
TEST_IMAGES_DIR = Path(__file__).parent / "fixtures" / "images"
TEST_IMAGE_1 = TEST_IMAGES_DIR / "test1.jpg"
TEST_IMAGE_2 = TEST_IMAGES_DIR / "test2.jpg"

@pytest.fixture
def mock_client():
    """モッククライアントのフィクスチャ"""
    client = MagicMock(spec=OllamaMCPClient)
    client.process_query = AsyncMock()
    client.process_multimodal_query = AsyncMock()
    client.chat_with_images = AsyncMock()
    return client

@pytest.fixture
def agent(mock_client):
    """エージェントのフィクスチャ"""
    return OllamaMCPAgent(client=mock_client)

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

@pytest.mark.asyncio
async def test_run_with_images_no_planning(agent, mock_client):
    """計画なしでの画像付きタスク実行のテスト"""
    # プランナーを無効化
    agent.planner = None
    
    # モックのレスポンス
    mock_response = "Generated text about the images"
    mock_client.process_multimodal_query.return_value = mock_response
    
    response = await agent.run_with_images(
        "Describe these images",
        [TEST_IMAGE_1, TEST_IMAGE_2]
    )
    
    assert response == mock_response
    mock_client.process_multimodal_query.assert_called_once()

@pytest.mark.asyncio
async def test_run_with_images_with_planning(agent, mock_client):
    """計画ありでの画像付きタスク実行のテスト"""
    # モックのレスポンス
    mock_step_response = "Step response about the images"
    mock_client.process_multimodal_query.return_value = mock_step_response
    
    # プランナーのモック
    mock_planner = MagicMock()
    mock_planner.create_plan = AsyncMock(return_value=[
        "Step 1: Analyze images",
        "Step 2: Generate description"
    ])
    agent.planner = mock_planner
    
    response = await agent.run_with_images(
        "Describe these images",
        [TEST_IMAGE_1, TEST_IMAGE_2]
    )
    
    assert mock_step_response in response
    assert mock_client.process_multimodal_query.call_count == 2

@pytest.mark.asyncio
async def test_execute_step_with_images(agent, mock_client):
    """画像付きステップ実行のテスト"""
    # モックのレスポンス
    mock_response = "Step response about the images"
    mock_client.process_multimodal_query.return_value = mock_response
    
    response = await agent.execute_step_with_images(
        "Analyze these images",
        [TEST_IMAGE_1, TEST_IMAGE_2]
    )
    
    assert response == mock_response
    mock_client.process_multimodal_query.assert_called_once()

@pytest.mark.asyncio
async def test_chat_with_images(agent, mock_client):
    """画像付きチャットのテスト"""
    # モックのレスポンス
    mock_response = "Chat response about the images"
    mock_client.chat_with_images.return_value = mock_response
    
    response = await agent.chat_with_images(
        "What do you see in these images?",
        [TEST_IMAGE_1, TEST_IMAGE_2]
    )
    
    assert response == mock_response
    mock_client.chat_with_images.assert_called_once()

@pytest.mark.asyncio
async def test_run_with_images_with_memory(agent, mock_client):
    """メモリ付きでの画像付きタスク実行のテスト"""
    # モックのレスポンス
    mock_response = "Generated text about the images"
    mock_client.process_multimodal_query.return_value = mock_response
    
    # プランナーを無効化
    agent.planner = None
    
    # メモリの状態を確認
    assert len(agent.memory.messages) == 0
    
    response = await agent.run_with_images(
        "Describe these images",
        [TEST_IMAGE_1, TEST_IMAGE_2]
    )
    
    assert response == mock_response
    assert len(agent.memory.messages) == 2  # ユーザーメッセージとアシスタントの応答
    assert agent.memory.messages[0]["role"] == "user"
    assert agent.memory.messages[1]["role"] == "assistant" 