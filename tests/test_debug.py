"""
デバッグユーティリティのテストケース
"""
import json
import os
import tempfile
from typing import Dict, Any

import pytest

from ollama_mcp.debug import DebugLogger, LogEntry

def test_log_entry():
    """ログエントリのテスト"""
    message = "テストメッセージ"
    level = "info"
    data = {"key": "value"}
    
    entry = LogEntry(message, level, data)
    
    assert entry.message == message
    assert entry.level == level
    assert entry.data == data
    assert isinstance(entry.timestamp, float)
    
    # 辞書形式への変換テスト
    entry_dict = entry.to_dict()
    assert entry_dict["message"] == message
    assert entry_dict["level"] == level
    assert entry_dict["data"] == data
    assert isinstance(entry_dict["timestamp"], float)

def test_debug_logger_initialization():
    """デバッグロガーの初期化テスト"""
    logger = DebugLogger(level="debug")
    
    assert logger.level == "debug"
    assert logger.log_file is None
    assert isinstance(logger.logs, list)
    assert len(logger.logs) == 0

def test_debug_logger_log():
    """デバッグロガーのログ記録テスト"""
    logger = DebugLogger()
    
    # 基本的なログ記録
    logger.log("テストメッセージ", "info")
    assert len(logger.logs) == 1
    assert isinstance(logger.logs[0], LogEntry)
    
    # データ付きのログ記録
    data = {"test": "value"}
    logger.log("データ付きメッセージ", "debug", data)
    assert len(logger.logs) == 2
    assert logger.logs[1].data == data

def test_debug_logger_export():
    """ログエクスポートのテスト"""
    logger = DebugLogger()
    logger.log("テストメッセージ1", "info")
    logger.log("テストメッセージ2", "debug", {"data": "test"})
    
    # 一時ファイルにエクスポート
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        logger.export_logs(temp_file.name)
        
        # エクスポートされたファイルを読み込んで検証
        with open(temp_file.name, "r") as f:
            exported = json.load(f)
            assert len(exported) == 2
            assert exported[0]["message"] == "テストメッセージ1"
            assert exported[1]["message"] == "テストメッセージ2"
        
        # 一時ファイルを削除
        os.unlink(temp_file.name)

def test_debug_logger_recent_logs():
    """最近のログ取得テスト"""
    logger = DebugLogger()
    
    # 複数のログを記録
    for i in range(5):
        logger.log(f"メッセージ{i}", "info")
    
    # 最近のログを取得
    recent = logger.get_recent_logs(3)
    assert len(recent) == 3
    assert recent[0]["message"] == "メッセージ2"
    assert recent[2]["message"] == "メッセージ4"

def test_debug_logger_message_inspection():
    """メッセージ検査機能のテスト"""
    logger = DebugLogger()
    
    # メッセージ検査を有効化
    logger.enable_message_inspection(show_headers=True)
    assert logger.show_headers is True
    
    # ツールコールトレースを有効化
    logger.enable_tool_call_tracing()
    assert logger.trace_tool_calls is True 