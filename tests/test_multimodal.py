"""
マルチモーダルモデルのテスト
"""
import base64
from pathlib import Path
import pytest
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock

from ollama_mcp.models.multimodal import MultimodalModel

# テスト用の画像パス
TEST_IMAGES_DIR = Path(__file__).parent / "fixtures" / "images"
TEST_IMAGE_1 = TEST_IMAGES_DIR / "test1.jpg"
TEST_IMAGE_2 = TEST_IMAGES_DIR / "test2.jpg"

@pytest.fixture
def multimodal_model():
    """マルチモーダルモデルのフィクスチャ"""
    return MultimodalModel(model_name="gemma")

@pytest.mark.asyncio
async def test_process_image(multimodal_model):
    """画像処理のテスト"""
    # 画像が存在することを確認
    assert TEST_IMAGE_1.exists()
    
    # 画像を処理
    base64_data = await multimodal_model.process_image(TEST_IMAGE_1)
    
    # base64形式であることを確認
    try:
        decoded_data = base64.b64decode(base64_data)
        assert len(decoded_data) > 0
    except Exception as e:
        pytest.fail(f"Invalid base64 data: {e}")

@pytest.mark.asyncio
async def test_generate_with_images(multimodal_model):
    """画像付きテキスト生成のテスト"""
    # モックのレスポンス
    mock_response = {
        "response": "Generated text about the images",
        "context": ["some context"]
    }

    # aiohttp.ClientSessionをモック化
    mock_session = AsyncMock()
    mock_response_obj = AsyncMock()
    mock_response_obj.raise_for_status = AsyncMock()
    mock_response_obj.json = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.post = AsyncMock(return_value=mock_response_obj)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        response = await multimodal_model.generate_with_images(
            "Describe these images",
            [TEST_IMAGE_1, TEST_IMAGE_2]
        )

    assert response == "Generated text about the images"
    assert multimodal_model.context == ["some context"]

@pytest.mark.asyncio
async def test_chat_with_images(multimodal_model):
    """画像付きチャットのテスト"""
    # モックのレスポンス
    mock_response = {
        "message": {
            "content": "Chat response about the images"
        }
    }

    # aiohttp.ClientSessionをモック化
    mock_session = AsyncMock()
    mock_response_obj = AsyncMock()
    mock_response_obj.raise_for_status = AsyncMock()
    mock_response_obj.json = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.post = AsyncMock(return_value=mock_response_obj)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        response = await multimodal_model.chat_with_images(
            "What do you see in these images?",
            [TEST_IMAGE_1, TEST_IMAGE_2]
        )

    assert response == "Chat response about the images"

@pytest.mark.asyncio
async def test_process_image_not_found(multimodal_model):
    """存在しない画像のテスト"""
    with pytest.raises(FileNotFoundError):
        await multimodal_model.process_image("nonexistent.jpg")

@pytest.mark.asyncio
async def test_generate_with_images_error(multimodal_model):
    """画像付きテキスト生成のエラーテスト"""
    # エラーを発生させるモック
    mock_session = AsyncMock()
    mock_response_obj = AsyncMock()
    mock_response_obj.raise_for_status = AsyncMock(side_effect=aiohttp.ClientError())
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.post = AsyncMock(return_value=mock_response_obj)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(aiohttp.ClientError):
            await multimodal_model.generate_with_images(
                "This should fail",
                [TEST_IMAGE_1]
            ) 