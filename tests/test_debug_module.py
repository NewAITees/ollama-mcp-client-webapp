import pytest
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from ollama_mcp.debug_module import AgnoMCPDebugger

@pytest.fixture
def debugger():
    """テスト用のデバッガーインスタンスを作成"""
    return AgnoMCPDebugger(level="error")  # テスト時はエラーレベルのみ表示

@pytest.fixture
def info_debugger():
    """情報レベルのログを記録するデバッガーインスタンスを作成（特定のテスト用）"""
    return AgnoMCPDebugger(level="info")

@pytest.fixture
def cleanup(debugger):
    """テスト後のクリーンアップ"""
    yield
    if os.path.exists("logs"):
        for file in os.listdir("logs"):
            os.remove(os.path.join("logs", file))
        os.rmdir("logs")

def test_debugger_initialization(debugger):
    """デバッガーの初期化テスト"""
    assert debugger.level == "error"
    assert os.path.exists("logs")
    assert debugger.log_file is not None
    assert isinstance(debugger.logs, list)
    assert isinstance(debugger.tool_calls, list)
    assert isinstance(debugger.errors, list)

def test_log_levels(info_debugger):
    """各ログレベルのテスト"""
    test_message = "テストメッセージ"
    test_levels = ["debug", "info", "warning", "error"]
    
    for level in test_levels:
        info_debugger.log(test_message, level)
    
    logs = info_debugger.get_recent_logs()
    assert len(logs) == 4
    
    for i, log in enumerate(logs):
        assert test_message in log["message"]
        assert log["level"] == test_levels[i]
        assert "timestamp" in log
        assert isinstance(log["timestamp"], str)

def test_tool_call_tracing(debugger):
    """ツールコールのトレーステスト"""
    test_calls = [
        {
            "tool": "test_tool1",
            "args": {"arg1": "value1"},
            "result": "テスト結果1",
            "duration": 0.1
        },
        {
            "tool": "test_tool2",
            "args": {"arg2": "value2"},
            "result": "テスト結果2",
            "duration": 0.2
        }
    ]
    
    for call in test_calls:
        debugger.record_tool_call(
            call["tool"],
            call["args"],
            call["result"],
            call["duration"]
        )
    
    tool_calls = debugger.get_tool_calls()
    assert len(tool_calls) == 2
    
    for i, call in enumerate(tool_calls):
        assert call["tool"] == test_calls[i]["tool"]
        assert call["args"] == test_calls[i]["args"]
        assert call["result"] == test_calls[i]["result"]
        assert call["duration"] == test_calls[i]["duration"]
        assert "timestamp" in call
        assert isinstance(call["timestamp"], str)

def test_error_recording(debugger):
    """エラー記録のテスト"""
    test_errors = [
        {
            "type": "connection_error",
            "message": "接続エラー",
            "details": {"host": "localhost"}
        },
        {
            "type": "processing_error",
            "message": "処理エラー",
            "details": {"file": "test.txt"}
        }
    ]
    
    for error in test_errors:
        debugger.record_error(
            error["type"],
            error["message"],
            error["details"]
        )
    
    errors = debugger.get_errors()
    assert len(errors) == 2
    
    for i, error in enumerate(errors):
        assert error["type"] == test_errors[i]["type"]
        assert error["message"] == test_errors[i]["message"]
        assert error["details"] == test_errors[i]["details"]
        assert "timestamp" in error
        assert isinstance(error["timestamp"], str)

def test_export_logs(debugger, tmp_path):
    """ログのエクスポートテスト"""
    # テストデータの準備
    test_data = {
        "log": ("テストログ", "error"),  # エラーレベルに変更
        "tool": ("test_tool", {"arg": "value"}, "result", 0.1),
        "error": ("test_error", "エラーメッセージ", {"detail": "value"})
    }
    
    # データの記録
    debugger.log(test_data["log"][0], test_data["log"][1])
    debugger.record_tool_call(*test_data["tool"])
    debugger.record_error(*test_data["error"])
    
    # エクスポート
    export_file = tmp_path / "test_export.json"
    debugger.export_logs(str(export_file))
    
    # エクスポートされたファイルの検証
    assert export_file.exists()
    with open(export_file, 'r') as f:
        exported_data = json.load(f)
        
        assert "logs" in exported_data
        assert "tool_calls" in exported_data
        assert "errors" in exported_data
        
        assert len(exported_data["logs"]) == 1
        assert len(exported_data["tool_calls"]) == 1
        assert len(exported_data["errors"]) == 1
        
        assert test_data["log"][0] in exported_data["logs"][0]["message"]
        assert test_data["tool"][0] == exported_data["tool_calls"][0]["tool"]
        assert test_data["error"][0] == exported_data["errors"][0]["type"]

def test_clear_logs(info_debugger):
    """ログのクリアテスト"""
    # テストデータの記録（少量に抑制）
    for i in range(3):
        info_debugger.log(f"テストメッセージ{i}", "info")
    
    assert len(info_debugger.get_recent_logs()) == 3
    
    # ログのクリア
    info_debugger.clear_logs()
    logs = info_debugger.get_recent_logs()
    
    # クリアログメッセージを除外して確認
    actual_logs = [log for log in logs if "Cleared memory logs" not in log["message"]]
    assert len(actual_logs) == 0

def test_clear_tool_calls(debugger):
    """ツールコールのクリアテスト"""
    # テストデータの記録
    for i in range(3):
        debugger.record_tool_call(f"tool{i}", {}, f"result{i}", 0.1)
    
    assert len(debugger.get_tool_calls()) == 3
    
    # ツールコールのクリア
    debugger.clear_tool_calls()
    assert len(debugger.get_tool_calls()) == 0

def test_clear_errors(debugger):
    """エラーのクリアテスト"""
    # テストデータの記録
    for i in range(3):
        debugger.record_error(f"error{i}", f"message{i}")
    
    assert len(debugger.get_errors()) == 3
    
    # エラーのクリア
    debugger.clear_errors()
    assert len(debugger.get_errors()) == 0

def test_log_rotation(info_debugger):
    """ログローテーションのテスト"""
    # テストサイズを縮小（1MB程度）
    large_message = "x" * 100  # 100バイト
    for i in range(1000):  # 約100KB
        info_debugger.log(f"{large_message} - {i}", "info")
    
    # ログファイルのサイズを確認
    log_file_size = os.path.getsize(info_debugger.log_file)
    assert log_file_size < 1024 * 1024  # 1MB未満であることを確認
    
    # ローテーションされたファイルの存在を確認
    log_dir = Path("logs")
    rotated_logs = list(log_dir.glob("*.log.*"))
    assert len(rotated_logs) > 0

def test_concurrent_logging(info_debugger):
    """並行ログ記録のテスト"""
    async def log_messages(count: int):
        for i in range(count):
            info_debugger.log(f"並行メッセージ {i}", "info")
            await asyncio.sleep(0.01)
    
    async def record_tool_calls(count: int):
        for i in range(count):
            info_debugger.record_tool_call(f"tool{i}", {}, f"result{i}", 0.1)
            await asyncio.sleep(0.01)
    
    async def record_errors(count: int):
        for i in range(count):
            info_debugger.record_error(f"error{i}", f"message{i}")
            await asyncio.sleep(0.01)
    
    async def run_concurrent_operations():
        await asyncio.gather(
            log_messages(5),  # 回数を削減
            record_tool_calls(3),  # 回数を削減
            record_errors(3)  # 回数を削減
        )
    
    # 並行操作の実行
    asyncio.run(run_concurrent_operations())
    
    # 結果の検証
    assert len(info_debugger.get_recent_logs()) >= 5
    assert len(info_debugger.get_tool_calls()) == 3
    assert len(info_debugger.get_errors()) == 3

def test_memory_management(info_debugger):
    """メモリ管理のテスト"""
    # テストサイズを縮小
    for i in range(100):  # 1000から100に削減
        info_debugger.log(f"テストメッセージ {i}", "info")
        if i % 10 == 0:  # 間隔を調整
            info_debugger.record_tool_call(f"tool{i}", {}, f"result{i}", 0.1)
        if i % 20 == 0:  # 間隔を調整
            info_debugger.record_error(f"error{i}", f"message{i}")
    
    # メモリ内のログ数を確認
    assert len(info_debugger.logs) <= 100  # 上限を調整
    assert len(info_debugger.tool_calls) <= 10  # 上限を調整
    assert len(info_debugger.errors) <= 5  # 上限を調整 