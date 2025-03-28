"""
Agnoを使用したマルチモーダル機能のモジュール
"""
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.media import Image as AgnoImage, Audio as AgnoAudio
from agno.tools.mcp import MCPTools

from .debug_module import AgnoMCPDebugger

class AgnoMultimodalIntegration:
    """
    Agnoベースのマルチモーダル統合クラス
    
    主な責務:
    - 画像、音声を含むマルチモーダル入力の処理
    - マルチモーダル対応モデルの管理
    - MCPツールとの連携
    """
    def __init__(self, model_name: str = "llama2", debug_level: str = "info"):
        """
        AgnoMultimodalIntegrationを初期化
        
        Args:
            model_name: 使用するモデル名（マルチモーダル対応モデル）
            debug_level: デバッグレベル
        """
        self.model_name = model_name
        self.debugger = AgnoMCPDebugger(level=debug_level)
        self.agent = None
        self.mcp_tools = None
        
        self.debugger.log(f"Initialized AgnoMultimodalIntegration with model {model_name}", "info")
    
    async def setup_agent(self, tools: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        エージェントをセットアップ
        
        Args:
            tools: 利用可能なツールのリスト（デフォルトは空リスト）
        """
        try:
            # Noneの場合は空リストに変換
            tools = tools or []
            
            # Ollamaモデルの設定
            model = Ollama(
                id=self.model_name,
                name="Ollama",
                provider="Ollama",
                supports_native_structured_outputs=True
            )
            
            # エージェントの初期化
            self.agent = Agent(
                model=model,
                tools=tools,
                show_tool_calls=True
            )
            
            self.mcp_tools = tools
            self.debugger.log(f"Agent setup completed with {len(tools)} tools", "info")
        except Exception as e:
            self.debugger.record_error(
                "agent_setup_error",
                f"Error setting up agent: {str(e)}"
            )
            raise
    
    async def process_with_images(self, 
                                prompt: str, 
                                image_paths: List[Union[str, Path]], 
                                stream: bool = False) -> str:
        """
        画像を含むプロンプトを処理
        
        Args:
            prompt: テキストプロンプト
            image_paths: 画像ファイルのパスのリスト
            stream: ストリーミング応答を使用するかどうか
            
        Returns:
            生成されたテキスト
        """
        if not self.agent:
            await self.setup_agent(self.mcp_tools)
        
        try:
            # 画像をAgnoイメージに変換
            images = []
            for img_path in image_paths:
                img_path = Path(img_path)
                if img_path.exists():
                    self.debugger.log(f"Adding image: {img_path}", "debug")
                    image = AgnoImage(filepath=str(img_path))
                    images.append(image)
                else:
                    error_msg = f"Image file not found: {img_path}"
                    self.debugger.record_error("image_not_found", error_msg)
                    raise FileNotFoundError(error_msg)
            
            # 画像処理を実行
            if stream:
                full_response = []
                
                self.debugger.log(f"Streaming response with {len(images)} images", "debug")
                async for response_chunk in self.agent.astream(prompt, images=images):
                    chunk_text = response_chunk.response
                    full_response.append(chunk_text)
                    self.debugger.log(f"Received chunk: {chunk_text}", "debug")
                
                result = "".join(full_response)
            else:
                self.debugger.log(f"Processing prompt with {len(images)} images", "debug")
                response = await self.agent.arun(prompt, images=images)
                result = response.response
            
            self.debugger.log(f"Multimodal processing complete", "info")
            return result
        except Exception as e:
            self.debugger.record_error(
                "multimodal_processing_error", 
                f"Error processing multimodal input: {str(e)}"
            )
            raise
    
    async def process_with_audio(self, 
                               prompt: str,
                               audio_path: Union[str, Path],
                               stream: bool = False) -> str:
        """
        音声を含むプロンプトを処理
        
        Args:
            prompt: テキストプロンプト
            audio_path: 音声ファイルのパス
            stream: ストリーミング応答を使用するかどうか
            
        Returns:
            生成されたテキスト
        """
        if not self.agent:
            await self.setup_agent(self.mcp_tools)
        
        try:
            # 音声をAgnoオーディオに変換
            audio_path = Path(audio_path)
            if audio_path.exists():
                self.debugger.log(f"Adding audio: {audio_path}", "debug")
                
                # 音声フォーマットを拡張子から判断
                format = audio_path.suffix.lstrip('.')
                with open(audio_path, "rb") as f:
                    audio_content = f.read()
                
                audio_file = AgnoAudio(content=audio_content, format=format)
            else:
                self.debugger.record_error(
                    "audio_not_found", 
                    f"Audio file not found: {audio_path}"
                )
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            # 音声処理を実行
            if stream:
                full_response = []
                
                self.debugger.log("Streaming response with audio file", "debug")
                async for response_chunk in self.agent.astream(prompt, audio=[audio_file]):
                    chunk_text = response_chunk.response
                    full_response.append(chunk_text)
                    self.debugger.log(f"Received chunk: {chunk_text}", "debug")
                
                result = "".join(full_response)
            else:
                self.debugger.log("Processing prompt with audio file", "debug")
                response = await self.agent.arun(prompt, audio=[audio_file])
                result = response.response
            
            self.debugger.log("Audio processing complete", "info")
            return result
        except Exception as e:
            self.debugger.record_error(
                "audio_processing_error",
                f"Error processing audio input: {str(e)}"
            )
            raise
    
    async def process_with_audio_streaming(self,
                                      prompt: str,
                                      audio_path: Union[str, Path]) -> str:
        """
        音声を含むプロンプトをストリーミング処理
        
        Args:
            prompt: テキストプロンプト
            audio_path: 音声ファイルのパス
            
        Returns:
            生成されたテキスト
        """
        return await self.process_with_audio(prompt, audio_path, stream=True)
    
    async def get_available_models(self) -> Dict[str, List[str]]:
        """
        利用可能なモデルの一覧を取得
        
        Returns:
            モデルタイプごとのモデル名のリスト
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        
                        return {
                            "text_models": [m["name"] for m in models if m.get("type") == "text"],
                            "multimodal_models": [m["name"] for m in models if m.get("type") == "multimodal"]
                        }
                    else:
                        self.debugger.record_error(
                            "model_fetch_error",
                            f"Failed to fetch models: {response.status}"
                        )
                        return {"text_models": [], "multimodal_models": []}
        except Exception as e:
            self.debugger.record_error(
                "model_fetch_error",
                f"Error fetching available models: {str(e)}"
            )
            return {"text_models": [], "multimodal_models": []}
    
    def set_model(self, model_name: str) -> None:
        """
        使用するモデルを変更
        
        Args:
            model_name: 新しいモデル名
        """
        self.model_name = model_name
        self.debugger.log(f"Model changed to {model_name}", "info")
        
        # エージェントを再設定
        if self.mcp_tools:
            asyncio.create_task(self.setup_agent(self.mcp_tools))
    
    async def close(self) -> None:
        """リソースを解放"""
        if self.mcp_tools:
            try:
                await self.mcp_tools.__aexit__(None, None, None)
                self.mcp_tools = None
                self.agent = None
                self.debugger.log("Resources cleaned up", "info")
            except Exception as e:
                self.debugger.record_error(
                    "cleanup_error",
                    f"Error during cleanup: {str(e)}"
                ) 