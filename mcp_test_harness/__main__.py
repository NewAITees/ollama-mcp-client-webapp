"""
MCPテストハーネスの実行エントリポイント
"""
import os
from .app import launch_app

if __name__ == "__main__":
    # 環境変数から実行環境を取得（デフォルトは開発環境）
    environment = os.environ.get("APP_ENV", "development")
    launch_app(environment) 