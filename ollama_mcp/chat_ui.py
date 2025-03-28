"""
Gradioを使用したチャットインターフェースの実装
"""
import gradio as gr
from loguru import logger
from agno.agent import Agent
from agno.models.ollama import Ollama

class ChatUI:
    def __init__(self):
        """チャットUIの初期化"""
        # システムプロンプトの設定
        system_prompt = """
あなたは優秀なAIアシスタントです。
ユーザーからの質問に対して、以下のガイドラインに従って回答してください：

1. 正確で信頼性の高い情報を提供する
2. 専門用語は必要に応じて説明を加える
3. 回答は論理的で分かりやすい構造にする
4. 必要に応じて具体例を示す
5. 不確かな情報は明確にその旨を伝える

また、技術的なトピックについては：
- 最新の情報を提供するよう心がける
- 実践的な応用例も含める
- 初心者にも理解しやすい説明を心がける
"""
        # エージェントの初期化
        self.agent = Agent(
            model=Ollama(
                id="gemma3:27b",
                options={
                    "system": system_prompt
                }
            ),
            markdown=True
        )
        self.chat_history = []
        
    def respond(self, message: str, history: list) -> str:
        """
        チャットメッセージに対する応答を生成
        
        Args:
            message (str): ユーザーからの入力メッセージ
            history (list): チャット履歴
            
        Returns:
            str: エージェントからの応答
        """
        try:
            logger.info(f"Received message: {message}")
            response = self.agent.run(message)
            # RunResponseオブジェクトからcontentフィールドを取得
            response_text = response.content
            logger.info(f"Generated response: {response_text}")
            return response_text
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"エラーが発生しました: {str(e)}"

    def launch(self, **kwargs):
        """
        Gradioインターフェースの起動
        
        Args:
            **kwargs: Gradioのlaunchメソッドに渡す追加のパラメータ
        """
        demo = gr.ChatInterface(
            fn=self.respond,
            title="Agnoエージェントチャット",
            description="Ollamaを使用したローカルLLMエージェントとチャットできます",
            theme="soft"
        )
        demo.launch(**kwargs)

def main():
    """メインエントリーポイント"""
    chat_ui = ChatUI()
    chat_ui.launch()

if __name__ == "__main__":
    main() 