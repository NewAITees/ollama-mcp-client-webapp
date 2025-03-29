# tests/test_visualizer.py

import pytest
import os
import time
from datetime import datetime
import matplotlib.pyplot as plt
from ollama_mcp.debug_module import AgnoMCPDebugger
from ollama_mcp.visualizer import MCPServerVisualizer, MCPVisualizer

@pytest.fixture
def debugger():
    """テスト用のデバッガーインスタンスを作成"""
    return AgnoMCPDebugger(level="info")

@pytest.fixture
def server_visualizer(debugger):
    """テスト用のサーバービジュアライザーインスタンスを作成"""
    return MCPServerVisualizer(debugger)

@pytest.fixture
def mcp_visualizer(debugger):
    """テスト用のMCPビジュアライザーインスタンスを作成"""
    return MCPVisualizer(debugger)

def test_server_visualizer_initialization(server_visualizer):
    """サーバービジュアライザーの初期化テスト"""
    assert server_visualizer.debugger is not None
    assert isinstance(server_visualizer.metrics_cache, dict)
    assert isinstance(server_visualizer.tool_stats, dict)
    assert isinstance(server_visualizer.error_stats, dict)
    assert isinstance(server_visualizer.performance_history, list)

def test_mcp_visualizer_initialization(mcp_visualizer):
    """MCPビジュアライザーの初期化テスト"""
    assert mcp_visualizer.debugger is not None
    assert mcp_visualizer.server_visualizer is not None
    assert isinstance(mcp_visualizer.update_interval, int)

def test_tool_stats_update(server_visualizer, debugger):
    """ツール統計更新のテスト"""
    # テスト用のツールコールを記録
    for i in range(3):
        debugger.record_tool_call(f"test_tool{i}", {"arg": "value"}, f"result{i}", 0.1 * (i + 1))
    
    # ツール統計を更新
    import asyncio
    asyncio.run(server_visualizer.update_tool_stats())
    
    # 結果を検証
    assert "test_tool0" in server_visualizer.tool_stats["calls"]
    assert "test_tool1" in server_visualizer.tool_stats["calls"]
    assert "test_tool2" in server_visualizer.tool_stats["calls"]
    
    assert server_visualizer.tool_stats["calls"]["test_tool0"] == 1
    assert server_visualizer.tool_stats["duration"]["test_tool1"] == 0.2
    assert server_visualizer.tool_stats["success"]["test_tool2"] == 100.0
    assert "test_tool0" in server_visualizer.tool_stats["last_used"]

def test_error_stats_update(server_visualizer, debugger):
    """エラー統計更新のテスト"""
    # テスト用のエラーを記録
    for i in range(3):
        debugger.record_error(f"error_type{i}", f"Error message {i}", {"tool": f"tool{i}"})
    
    # エラー統計を更新
    import asyncio
    asyncio.run(server_visualizer.update_error_stats())
    
    # 結果を検証
    assert "error_type0" in server_visualizer.error_stats["count"]
    assert "error_type1" in server_visualizer.error_stats["count"]
    assert "error_type2" in server_visualizer.error_stats["count"]
    
    assert server_visualizer.error_stats["count"]["error_type0"] == 1
    assert len(server_visualizer.error_stats["timeline"]) == 3
    assert "tool0" in server_visualizer.error_stats["sources"]
    assert "tool1" in server_visualizer.error_stats["sources"]
    assert "tool2" in server_visualizer.error_stats["sources"]

def test_chart_generation(server_visualizer):
    """チャート生成のテスト"""
    # 各チャートを生成
    tool_chart = server_visualizer.generate_tool_usage_chart()
    server_chart = server_visualizer.generate_server_status_chart()
    error_chart = server_visualizer.generate_error_trend_chart()
    perf_chart = server_visualizer.generate_performance_chart()
    error_dist_chart = server_visualizer.generate_error_distribution_chart()
    success_chart = server_visualizer.generate_tool_success_chart()
    
    # 結果を検証
    assert isinstance(tool_chart, plt.Figure)
    assert isinstance(server_chart, plt.Figure)
    assert isinstance(error_chart, plt.Figure)
    assert isinstance(perf_chart, plt.Figure)
    assert isinstance(error_dist_chart, plt.Figure)
    assert isinstance(success_chart, plt.Figure)

def test_table_generation(server_visualizer, debugger):
    """テーブル生成のテスト"""
    # テスト用のデータを準備
    debugger.record_tool_call("test_tool", {"arg": "value"}, "result", 0.1)
    debugger.record_error("test_error", "Error message", {"tool": "test_tool"})
    
    # 統計を更新
    import asyncio
    asyncio.run(server_visualizer.update_tool_stats())
    asyncio.run(server_visualizer.update_error_stats())
    
    # テーブルを生成
    tool_table = server_visualizer.get_tool_details_table()
    error_table = server_visualizer.get_error_details_table()
    
    # 結果を検証
    assert isinstance(tool_table, list)
    assert len(tool_table) >= 2  # ヘッダー行 + データ行
    assert tool_table[0][0] == "ツール名"
    
    assert isinstance(error_table, list)
    assert len(error_table) >= 2  # ヘッダー行 + データ行
    assert error_table[0][0] == "タイムスタンプ"

def test_metrics_summary(server_visualizer, debugger):
    """メトリクス要約のテスト"""
    # テスト用のデータを準備
    debugger.record_tool_call("test_tool", {"arg": "value"}, "result", 0.1)
    debugger.record_error("test_error", "Error message", {"tool": "test_tool"})
    
    # 統計を更新
    import asyncio
    asyncio.run(server_visualizer.update_tool_stats())
    asyncio.run(server_visualizer.update_error_stats())
    
    # メトリクス要約を取得
    summary = server_visualizer.get_metrics_summary()
    
    # 結果を検証
    assert isinstance(summary, dict)
    assert "timestamp" in summary
    assert "tool_metrics" in summary
    assert "error_metrics" in summary
    assert "total_calls" in summary["tool_metrics"]
    assert "total_errors" in summary["error_metrics"]