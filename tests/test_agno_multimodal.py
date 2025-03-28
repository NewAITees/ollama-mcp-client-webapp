import pytest
import os
import asyncio
from unittest.mock import Mock, patch, AsyncMock, mock_open
from ollama_mcp.agno_multimodal import AgnoMultimodalIntegration
from agno.agent import Agent
from agno.media import Image as AgnoImage, Audio as AgnoAudio

@pytest.fixture
def mock_agent():
    """テスト用のモックエージェントを作成"""
    mock = Mock(spec=Agent)
    mock.arun = AsyncMock()
    mock.astream = AsyncMock()
    return mock

@pytest.fixture
def mock_debugger():
    """テスト用のモックデバッガーを作成"""
    return Mock()

@pytest.fixture
def processor():
    """テスト用のAgnoMultimodalIntegrationインスタンスを作成"""
    return AgnoMultimodalIntegration(model_name="gemma")

@pytest.fixture
def test_image_path():
    """テスト用の画像ファイルパスを作成"""
    return "test_image.jpg"

@pytest.fixture
def test_audio_path():
    """テスト用の音声ファイルパスを作成"""
    return "test_audio.mp3"

@pytest.fixture
def test_video_path():
    """テスト用の動画ファイルパスを作成"""
    return "test_video.mp4"

@pytest.mark.asyncio
async def test_processor_initialization(processor):
    """プロセッサーの初期化テスト"""
    assert processor.model_name == "gemma"
    assert processor.debugger is not None
    assert processor.agent is None
    assert processor.mcp_tools is None

@pytest.mark.asyncio
async def test_setup_agent(processor, mock_agent):
    """エージェントのセットアップテスト"""
    mock_tools = Mock()
    
    with patch('agno.agent.Agent', return_value=mock_agent):
        await processor.setup_agent(mock_tools)
        
        assert processor.agent is not None
        assert processor.mcp_tools == mock_tools
        assert isinstance(processor.agent, Mock)

@pytest.mark.asyncio
async def test_process_with_images(processor, test_image_path, mock_agent):
    """画像処理テスト - 基本機能"""
    test_prompt = "画像について説明してください"
    mock_response = Mock(response="画像の説明")
    mock_agent.arun.return_value = mock_response
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('agno.media.Image', autospec=True) as mock_image, \
         patch('agno.agent.Agent', return_value=mock_agent):
        
        # 通常の処理テスト
        response = await processor.process_with_images(test_prompt, [test_image_path])
        assert response == "画像の説明"
        mock_agent.arun.assert_called_once()
        mock_image.assert_called_once_with(path=test_image_path)

@pytest.mark.asyncio
async def test_process_with_images_streaming(processor, test_image_path, mock_agent):
    """画像処理テスト - ストリーミング"""
    test_prompt = "画像について説明してください"
    mock_chunks = ["チャンク1", "チャンク2", "チャンク3"]
    
    async def mock_stream():
        for chunk in mock_chunks:
            yield Mock(response=chunk)
            await asyncio.sleep(0.1)
    
    mock_agent.astream.return_value = mock_stream()
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('agno.media.Image', autospec=True) as mock_image, \
         patch('agno.agent.Agent', return_value=mock_agent):
        
        response = await processor.process_with_images(test_prompt, [test_image_path], stream=True)
        assert response == "チャンク1チャンク2チャンク3"
        mock_agent.astream.assert_called_once()
        mock_image.assert_called_once_with(path=test_image_path)

@pytest.mark.asyncio
async def test_process_with_images_multiple(processor, mock_agent):
    """画像処理テスト - 複数画像"""
    test_prompt = "画像について説明してください"
    test_images = ["image1.jpg", "image2.jpg", "image3.jpg"]
    mock_response = Mock(response="複数画像の説明")
    mock_agent.arun.return_value = mock_response
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('agno.media.Image', autospec=True) as mock_image, \
         patch('agno.agent.Agent', return_value=mock_agent):
        
        response = await processor.process_with_images(test_prompt, test_images)
        assert response == "複数画像の説明"
        assert mock_image.call_count == 3
        mock_agent.arun.assert_called_once()

@pytest.mark.asyncio
async def test_process_with_audio(processor, test_audio_path, mock_agent):
    """音声処理テスト - 基本機能"""
    test_prompt = "音声を文字起こししてください"
    mock_response = Mock(response="音声の文字起こし")
    test_audio_data = b'test audio data'
    mock_agent.arun.return_value = mock_response
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('builtins.open', mock_open(read_data=test_audio_data)), \
         patch('agno.media.Audio', autospec=True) as mock_audio, \
         patch('agno.agent.Agent', return_value=mock_agent):
        
        response = await processor.process_with_audio(test_prompt, [test_audio_path])
        assert response == "音声の文字起こし"
        mock_agent.arun.assert_called_once()
        mock_audio.assert_called_once_with(content=test_audio_data, format='mp3')

@pytest.mark.asyncio
async def test_process_with_audio_streaming(processor, test_audio_path, mock_agent):
    """音声処理テスト - ストリーミング"""
    test_prompt = "音声を文字起こししてください"
    mock_chunks = ["チャンク1", "チャンク2", "チャンク3"]
    test_audio_data = b'test audio data'
    
    async def mock_stream():
        for chunk in mock_chunks:
            yield Mock(response=chunk)
            await asyncio.sleep(0.1)
    
    mock_agent.astream.return_value = mock_stream()
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('builtins.open', mock_open(read_data=test_audio_data)), \
         patch('agno.media.Audio', autospec=True) as mock_audio, \
         patch('agno.agent.Agent', return_value=mock_agent):
        
        response = await processor.process_with_audio(test_prompt, [test_audio_path], stream=True)
        assert response == "チャンク1チャンク2チャンク3"
        mock_agent.astream.assert_called_once()
        mock_audio.assert_called_once_with(content=test_audio_data, format='mp3')

@pytest.mark.asyncio
async def test_missing_file_error(processor, mock_agent):
    """ファイルが存在しない場合のエラー処理テスト"""
    test_prompt = "メディアを処理してください"
    missing_files = {
        "image": ["missing_image.jpg"],
        "audio": ["missing_audio.mp3"]
    }
    
    with patch('pathlib.Path.exists', return_value=False), \
         patch('agno.agent.Agent', return_value=mock_agent):
        
        # 画像ファイルが存在しない場合
        response = await processor.process_with_images(test_prompt, missing_files["image"])
        mock_agent.arun.assert_called_with(test_prompt, images=[])
        
        # 音声ファイルが存在しない場合
        response = await processor.process_with_audio(test_prompt, missing_files["audio"])
        mock_agent.arun.assert_called_with(test_prompt, audio=[])

@pytest.mark.asyncio
async def test_agent_error_handling(processor, test_image_path, test_audio_path):
    """エージェントエラーの処理テスト"""
    test_prompt = "メディアを処理してください"
    error_message = "エージェントエラー"
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('agno.agent.Agent') as mock_agent:
        mock_agent.return_value.arun = AsyncMock(side_effect=Exception(error_message))
        
        # 画像処理エラー
        with pytest.raises(Exception) as exc_info:
            await processor.process_with_images(test_prompt, [test_image_path])
        assert str(exc_info.value) == error_message
        
        # 音声処理エラー
        with pytest.raises(Exception) as exc_info:
            await processor.process_with_audio(test_prompt, [test_audio_path])
        assert str(exc_info.value) == error_message

@pytest.mark.asyncio
async def test_get_available_models(processor):
    """利用可能なモデルの取得テスト"""
    mock_response = {
        "models": [
            {"name": "llama2", "type": "text"},
            {"name": "gemma", "type": "multimodal"},
            {"name": "llava", "type": "multimodal"},
            {"name": "mistral", "type": "text"}
        ]
    }
    
    mock_session = AsyncMock()
    mock_response_obj = AsyncMock()
    mock_response_obj.status = 200
    mock_response_obj.json = AsyncMock(return_value=mock_response)
    mock_session.get.return_value = mock_response_obj
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        models = await processor.get_available_models()
        
        assert "text_models" in models
        assert "multimodal_models" in models
        assert "llama2" in models["text_models"]
        assert "mistral" in models["text_models"]
        assert "gemma" in models["multimodal_models"]
        assert "llava" in models["multimodal_models"]
        assert len(models["text_models"]) == 2
        assert len(models["multimodal_models"]) == 2

@pytest.mark.asyncio
async def test_get_available_models_error(processor):
    """モデル取得エラーのテスト"""
    mock_session = AsyncMock()
    mock_response_obj = AsyncMock()
    mock_response_obj.status = 500
    mock_session.get.return_value = mock_response_obj
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        models = await processor.get_available_models()
        
        assert models == {"text_models": [], "multimodal_models": []}

@pytest.mark.asyncio
async def test_set_model(processor):
    """モデル設定テスト"""
    new_model = "llava"
    processor.set_model(new_model)
    
    assert processor.model_name == new_model
    assert processor.agent is None  # エージェントがリセットされていることを確認 