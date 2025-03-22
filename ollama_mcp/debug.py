"""
デバッグと問題診断のためのユーティリティ
"""
import json
import time
from typing import Dict, List, Any, Optional

from loguru import logger

class LogEntry:
    """ログエントリを表現するクラス"""
    def __init__(self, message: str, level: str, data: Optional[Dict[str, Any]] = None):
        """
        LogEntryを初期化
        
        Args:
            message: ログメッセージ
            level: ログレベル
            data: 関連データ
        """
        self.timestamp = time.time()
        self.message = message
        self.level = level
        self.data = data or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        辞書形式に変換
        
        Returns:
            ログエントリの辞書表現
        """
        return {
            "timestamp": self.timestamp,
            "message": self.message,
            "level": self.level,
            "data": self.data
        }

class DebugLogger:
    """
    デバッグ情報のロギングと可視化
    
    主な責務:
    - メッセージの記録
    - ツールコールのトレース
    - エラーの診断
    - パフォーマンスの監視
    """
    def __init__(self, level: str = "info", log_file: Optional[str] = None):
        """
        DebugLoggerを初期化
        
        Args:
            level: ログレベル (debug, info, warning, error)
            log_file: ログファイルのパス
        """
        self.level = level
        self.log_file = log_file
        self.logs: List[LogEntry] = []
        self.show_headers = False
        self.trace_tool_calls = False
        
        # ロガーの設定
        logger.remove()
        logger.add(lambda msg: None, level=level.upper())  # ログ出力を抑制
        
        if log_file:
            logger.add(log_file, rotation="10 MB", level=level.upper())
    
    def log(self, message: str, level: str = "info", data: Optional[Dict[str, Any]] = None):
        """
        メッセージを記録
        
        Args:
            message: ログメッセージ
            level: ログレベル
            data: 関連するデータ
        """
        log_entry = LogEntry(message, level, data)
        getattr(logger, level)(message)
        self.logs.append(log_entry)
    
    def enable_message_inspection(self, show_headers: bool = True):
        """
        メッセージ検査を有効化
        
        Args:
            show_headers: ヘッダーを表示するかどうか
        """
        self.show_headers = show_headers
    
    def enable_tool_call_tracing(self):
        """ツールコールトレースを有効化"""
        self.trace_tool_calls = True
    
    def export_logs(self, file_path: str):
        """
        ログをエクスポート
        
        Args:
            file_path: エクスポート先のファイルパス
        """
        with open(file_path, "w") as f:
            logs_json = json.dumps([log.to_dict() for log in self.logs], indent=2)
            f.write(logs_json)
    
    def get_recent_logs(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        最近のログを取得
        
        Args:
            count: 取得するログの数
            
        Returns:
            最近のログのリスト
        """
        recent_logs = [log.to_dict() for log in self.logs[-count:]]
        return recent_logs 