import pytest
import os
import asyncio
from unittest.mock import Mock, patch, AsyncMock, mock_open
from ollama_mcp.agno_multimodal import AgnoMultimodalIntegration
from agno.agent import Agent
from agno.media import Image as AgnoImage, Audio as AgnoAudio

@pytest.fixture
def mock_agent():
    """モックエージェントのフィクスチャ"""
    agent = Mock(spec=Agent)
    agent.arun = AsyncMock()
    agent.astream = AsyncMock()
    return agent

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
    """エージェントセットアップテスト"""
    # ツールなしの場合
    with patch('agno.agent.Agent', return_value=mock_agent), \
         patch('agno.models.ollama.Ollama', return_value=Mock()):
        await processor.setup_agent()
        assert processor.agent is not None
        assert processor.mcp_tools == []
        
        # 空リストの場合
        await processor.setup_agent([])
        assert processor.agent is not None
        assert processor.mcp_tools == []
        
        # ツールありの場合
        test_tools = [{"name": "test_tool", "description": "Test tool"}]
        await processor.setup_agent(test_tools)
        assert processor.agent is not None
        assert processor.mcp_tools == test_tools

@pytest.mark.asyncio
async def test_process_with_images(processor, mock_agent):
    """画像処理テスト"""
    test_prompt = "画像について説明してください"
    test_image_path = "test_image.jpg"
    mock_response = Mock(response="画像の説明")
    mock_agent.arun.return_value = mock_response
    
    # モックの設定
    mock_image = Mock(spec=AgnoImage)
    mock_image.filepath = test_image_path
    mock_image.content = b"test image content"
    mock_image.format = "jpg"
    mock_image.model_dump = Mock(return_value={"filepath": test_image_path})
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('agno.media.Image', return_value=mock_image), \
         patch('agno.agent.Agent', return_value=mock_agent), \
         patch('agno.models.ollama.Ollama', return_value=Mock()):
        
        response = await processor.process_with_images(test_prompt, [test_image_path])
        assert response == "画像の説明"
        mock_agent.arun.assert_called_once()

@pytest.mark.asyncio
async def test_process_with_images_streaming(processor, mock_agent):
    """画像ストリーミング処理テスト"""
    test_prompt = "画像について説明してください"
    test_image_path = "test_image.jpg"
    mock_chunks = ["チャンク1", "チャンク2", "チャンク3"]
    
    # モックの設定
    mock_image = Mock(spec=AgnoImage)
    mock_image.filepath = test_image_path
    mock_image.content = b"test image content"
    mock_image.format = "jpg"
    mock_image.model_dump = Mock(return_value={"filepath": test_image_path})
    
    async def mock_stream():
        for chunk in mock_chunks:
            yield Mock(response=chunk)
            await asyncio.sleep(0.1)
    
    mock_agent.astream = AsyncMock(return_value=mock_stream())
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('agno.media.Image', return_value=mock_image), \
         patch('agno.agent.Agent', return_value=mock_agent), \
         patch('agno.models.ollama.Ollama', return_value=Mock()):
        
        response = await processor.process_with_images(test_prompt, [test_image_path], stream=True)
        assert response == "チャンク1チャンク2チャンク3"
        assert mock_agent.astream.call_count == 1

@pytest.mark.asyncio
async def test_process_with_images_multiple(processor, mock_agent):
    """画像処理テスト - 複数画像"""
    test_prompt = "画像について説明してください"
    test_images = ["image1.jpg", "image2.jpg", "image3.jpg"]
    mock_response = Mock(response="複数画像の説明")
    mock_agent.arun.return_value = mock_response
    
    # モックの設定
    mock_images = []
    for img_path in test_images:
        mock_img = Mock(spec=AgnoImage)
        mock_img.filepath = img_path
        mock_img.content = b"test image content"
        mock_img.format = "jpg"
        mock_img.model_dump = Mock(return_value={"filepath": img_path})
        mock_images.append(mock_img)
    
    mock_image = Mock(side_effect=mock_images)
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('agno.media.Image', side_effect=mock_images), \
         patch('agno.agent.Agent', return_value=mock_agent), \
         patch('agno.models.ollama.Ollama', return_value=Mock()):
        
        response = await processor.process_with_images(test_prompt, test_images)
        assert response == "複数画像の説明"
        assert mock_agent.arun.call_count == 1
        assert len(mock_images) == 3

@pytest.mark.asyncio
async def test_process_with_audio(processor, mock_agent):
    """音声処理テスト"""
    test_prompt = "音声について説明してください"
    test_audio_path = "test_audio.wav"
    mock_response = Mock(response="音声の文字起こし")
    mock_agent.arun.return_value = mock_response
    
    # モックの設定
    mock_audio = Mock(spec=AgnoAudio)
    mock_audio.filepath = test_audio_path
    mock_audio.content = b"test audio content"
    mock_audio.format = "wav"
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('agno.media.Audio', return_value=mock_audio), \
         patch('agno.agent.Agent', return_value=mock_agent), \
         patch('agno.models.ollama.Ollama', return_value=Mock()):
        
        response = await processor.process_with_audio(test_prompt, test_audio_path)
        assert response == "音声の文字起こし"
        mock_agent.arun.assert_called_once()

@pytest.mark.asyncio
async def test_process_with_audio_streaming(processor, mock_agent):
    """音声ストリーミング処理テスト"""
    test_prompt = "音声について説明してください"
    test_audio_path = "test_audio.wav"
    mock_chunks = ["チャンク1", "チャンク2", "チャンク3"]
    
    # モックの設定
    mock_audio = Mock(spec=AgnoAudio)
    mock_audio.filepath = test_audio_path
    mock_audio.content = b"test audio content"
    mock_audio.format = "wav"
    
    async def mock_stream():
        for chunk in mock_chunks:
            yield chunk
            await asyncio.sleep(0.1)
    
    mock_agent.astream.return_value = mock_stream()
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('agno.media.Audio', return_value=mock_audio), \
         patch('agno.agent.Agent', return_value=mock_agent), \
         patch('agno.models.ollama.Ollama', return_value=Mock()):
        
        response = await processor.process_with_audio_streaming(test_prompt, test_audio_path)
        assert response == "".join(mock_chunks)
        mock_agent.astream.assert_called_once()

@pytest.mark.asyncio
async def test_missing_file_error(processor, mock_agent):
    """ファイルが存在しない場合のエラーハンドリングテスト"""
    test_prompt = "メディアを処理してください"
    missing_files = {
        "image": "missing_image.jpg",
        "audio": "missing_audio.wav"
    }
    
    # モックの設定
    mock_image = Mock(spec=AgnoImage)
    mock_image.filepath = missing_files["image"]
    mock_image.model_dump = Mock(return_value={"filepath": missing_files["image"]})
    
    mock_audio = Mock(spec=AgnoAudio)
    mock_audio.filepath = missing_files["audio"]
    
    with patch('pathlib.Path.exists', return_value=False), \
         patch('agno.media.Image', return_value=mock_image), \
         patch('agno.media.Audio', return_value=mock_audio), \
         patch('agno.agent.Agent', return_value=mock_agent), \
         patch('agno.models.ollama.Ollama', return_value=Mock()):
        
        # 画像ファイルが存在しない場合
        with pytest.raises(FileNotFoundError) as exc_info:
            await processor.process_with_images(test_prompt, [missing_files["image"]])
        assert str(exc_info.value) == f"Image file not found: {missing_files['image']}"
        
        # 音声ファイルが存在しない場合
        with pytest.raises(FileNotFoundError) as exc_info:
            await processor.process_with_audio(test_prompt, missing_files["audio"])
        assert str(exc_info.value) == f"Audio file not found: {missing_files['audio']}"

@pytest.mark.asyncio
async def test_agent_error_handling(processor, mock_agent):
    """エージェントエラーハンドリングテスト"""
    test_prompt = "メディアを処理してください"
    error_message = "エージェントエラー"
    
    # モックの設定
    mock_image = Mock(spec=AgnoImage)
    mock_image.filepath = "test_image.jpg"
    mock_image.content = b"test image content"
    mock_image.format = "jpg"
    mock_image.model_dump = Mock(side_effect=Exception(error_message))
    
    mock_audio = Mock(spec=AgnoAudio)
    mock_audio.filepath = "test_audio.wav"
    mock_audio.content = b"test audio content"
    mock_audio.format = "wav"
    
    mock_agent.arun.side_effect = Exception(error_message)
    mock_agent.astream.side_effect = Exception(error_message)
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('agno.media.Image', return_value=mock_image), \
         patch('agno.media.Audio', return_value=mock_audio), \
         patch('agno.agent.Agent', return_value=mock_agent), \
         patch('agno.models.ollama.Ollama', return_value=Mock()):
        
        # 画像処理時のエラー
        with pytest.raises(Exception) as exc_info:
            await processor.process_with_images(test_prompt, ["test_image.jpg"])
        assert str(exc_info.value) == error_message
        
        # 音声処理時のエラー
        with pytest.raises(Exception) as exc_info:
            await processor.process_with_audio(test_prompt, "test_audio.wav")
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
    
    # モックの設定
    mock_response_obj = AsyncMock()
    mock_response_obj.status = 200
    mock_response_obj.json = AsyncMock(return_value=mock_response)
    
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_response_obj)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    
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
        
        mock_session.get.assert_called_once_with("http://localhost:11434/api/tags")
        mock_response_obj.json.assert_called_once()

@pytest.mark.asyncio
async def test_get_available_models_error(processor):
    """モデル取得エラーのテスト"""
    # モックの修正
    mock_response_obj = AsyncMock()
    mock_response_obj.status = 500
    
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_response_obj)
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        with patch.object(mock_session, '__aenter__', return_value=mock_session):
            with patch.object(mock_session, '__aexit__', return_value=None):
                models = await processor.get_available_models()
                
                assert models == {"text_models": [], "multimodal_models": []}
                
                # モックの呼び出し確認
                mock_session.get.assert_called_once_with("http://localhost:11434/api/tags")

@pytest.mark.asyncio
async def test_set_model(processor):
    """モデル設定テスト"""
    new_model = "llava"
    processor.set_model(new_model)
    
    assert processor.model_name == new_model
    assert processor.agent is None  # エージェントがリセットされていることを確認 