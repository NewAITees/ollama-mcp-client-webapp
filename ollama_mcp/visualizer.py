"""
MCPサーバー情報とメトリクスの可視化モジュール

主な機能:
- サーバー状態の可視化
- ツール使用統計の表示
- エラー分析のグラフ表示
- パフォーマンスメトリクスの視覚化
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # GUIが不要なバックエンドを使用
import io
import base64
from PIL import Image

import gradio as gr

from ollama_mcp.debug_module import AgnoMCPDebugger

class MCPServerVisualizer:
    """
    MCPサーバー情報の可視化クラス
    
    主な責務:
    - サーバーメトリクスの収集と表示
    - ツール使用状況の分析
    - エラーパターンの可視化
    - リアルタイムパフォーマンスのモニタリング
    """
    def __init__(self, debugger: AgnoMCPDebugger):
        """
        MCPServerVisualizer を初期化
        
        Args:
            debugger: AgnoMCPDebugger インスタンス
        """
        self.debugger = debugger
        self.metrics_cache = {}
        self.last_update = datetime.now()
        self.update_interval = 5  # 秒
        self.logger = logging.getLogger("mcp-visualizer")
        
        # ツール統計の保存
        self.tool_stats = {
            "calls": {},      # ツールごとの呼び出し回数
            "duration": {},   # ツールごとの平均実行時間
            "success": {},    # ツールごとの成功率
            "last_used": {}   # ツールごとの最終使用時刻
        }
        
        # エラー統計の保存
        self.error_stats = {
            "count": {},      # エラータイプごとの発生回数
            "timeline": [],   # 時系列でのエラー発生
            "sources": {}     # エラーの発生源
        }
        
        # パフォーマンス情報
        self.performance_history = []
        
        self.debugger.log("MCPServerVisualizer initialized", "info")
    
    async def update_metrics(self) -> Dict[str, Any]:
        """
        サーバーメトリクスを更新
        
        Returns:
            更新されたメトリクス
        """
        now = datetime.now()
        
        # 前回の更新から十分な時間が経過していない場合はキャッシュを返す
        if (now - self.last_update).total_seconds() < self.update_interval and self.metrics_cache:
            return self.metrics_cache
        
        try:
            # メトリクスの収集
            self.last_update = now
            
            # ツール使用統計の更新
            await self.update_tool_stats()
            
            # エラー統計の更新
            await self.update_error_stats()
            
            # パフォーマンス情報の収集
            response_times = self._calculate_response_times()
            error_rate = self._calculate_error_rate()
            
            # メトリクスをまとめる
            metrics = {
                "timestamp": now.isoformat(),
                "tool_stats": self.tool_stats,
                "error_stats": self.error_stats,
                "performance": {
                    "response_times": response_times,
                    "error_rate": error_rate,
                    "requests_per_minute": len(self.performance_history) / 10 if self.performance_history else 0
                }
            }
            
            # メトリクスをキャッシュに保存
            self.metrics_cache = metrics
            return metrics
            
        except Exception as e:
            self.debugger.record_error(
                "metrics_update_error",
                f"Error updating metrics: {str(e)}"
            )
            # エラーが発生した場合も前回のキャッシュを返す
            return self.metrics_cache or {"error": str(e)}
    
    async def update_tool_stats(self) -> None:
        """ツール使用統計を更新"""
        try:
            # 最近のツールコールを取得（最大100件）
            tool_calls = self.debugger.get_tool_calls(100)
            
            if not tool_calls:
                return
            
            # ツールごとの統計を計算
            calls = {}
            durations = {}
            success = {}
            last_used = {}
            
            for call in tool_calls:
                tool_name = call.get("tool", "unknown")
                timestamp = call.get("timestamp", "")
                duration = call.get("duration", 0)
                result = call.get("result", None)
                
                # 呼び出し回数
                if tool_name in calls:
                    calls[tool_name] += 1
                else:
                    calls[tool_name] = 1
                
                # 実行時間
                if tool_name in durations:
                    durations[tool_name].append(duration)
                else:
                    durations[tool_name] = [duration]
                
                # 成功したかどうか（結果がエラーを含まなければ成功と見なす）
                is_success = True
                if isinstance(result, str) and ("error" in result.lower() or "exception" in result.lower()):
                    is_success = False
                
                if tool_name in success:
                    success[tool_name]["total"] += 1
                    if is_success:
                        success[tool_name]["success"] += 1
                else:
                    success[tool_name] = {"total": 1, "success": 1 if is_success else 0}
                
                # 最終使用時刻
                last_used[tool_name] = timestamp
            
            # 平均実行時間を計算
            avg_durations = {}
            for tool_name, times in durations.items():
                avg_durations[tool_name] = sum(times) / len(times)
            
            # 成功率を計算
            success_rates = {}
            for tool_name, stats in success.items():
                success_rates[tool_name] = (stats["success"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            
            # 統計を更新
            self.tool_stats["calls"] = calls
            self.tool_stats["duration"] = avg_durations
            self.tool_stats["success"] = success_rates
            self.tool_stats["last_used"] = last_used
            
        except Exception as e:
            self.debugger.record_error(
                "tool_stats_update_error",
                f"Error updating tool statistics: {str(e)}"
            )
    
    async def update_error_stats(self) -> None:
        """エラー統計を更新"""
        try:
            # エラーログを取得（最大50件）
            errors = self.debugger.get_errors(50)
            
            if not errors:
                return
            
            # エラータイプごとの集計
            error_counts = {}
            error_timeline = []
            error_sources = {}
            
            for error in errors:
                error_type = error.get("type", "unknown")
                timestamp = error.get("timestamp", "")
                message = error.get("message", "")
                details = error.get("details", {})
                
                # エラー数を集計
                if error_type in error_counts:
                    error_counts[error_type] += 1
                else:
                    error_counts[error_type] = 1
                
                # タイムライン用のデータ
                if timestamp:
                    error_timeline.append({
                        "timestamp": timestamp,
                        "type": error_type
                    })
                
                # エラー発生源（ツール名など）
                source = details.get("tool", "unknown")
                if source in error_sources:
                    error_sources[source] += 1
                else:
                    error_sources[source] = 1
            
            # 統計を更新
            self.error_stats["count"] = error_counts
            self.error_stats["timeline"] = sorted(error_timeline, key=lambda x: x["timestamp"])
            self.error_stats["sources"] = error_sources
            
        except Exception as e:
            self.debugger.record_error(
                "error_stats_update_error",
                f"Error updating error statistics: {str(e)}"
            )
    
    def _calculate_response_times(self) -> Dict[str, float]:
        """応答時間の統計を計算"""
        # 最近の応答時間のデータを取得
        tool_calls = self.debugger.get_tool_calls(20)
        
        if not tool_calls:
            return {"avg": 0, "min": 0, "max": 0, "p95": 0}
        
        # 応答時間のリストを作成
        durations = [call.get("duration", 0) for call in tool_calls]
        
        # 統計値を計算
        return {
            "avg": sum(durations) / len(durations) if durations else 0,
            "min": min(durations) if durations else 0,
            "max": max(durations) if durations else 0,
            "p95": sorted(durations)[int(len(durations) * 0.95)] if len(durations) >= 20 else max(durations) if durations else 0
        }
    
    def _calculate_error_rate(self) -> float:
        """エラー率を計算"""
        # 最近のログ数と最近のエラー数を取得
        logs = self.debugger.get_recent_logs(100)
        errors = self.debugger.get_errors(50)
        
        if not logs:
            return 0.0
        
        # 最近のエラー（過去1時間以内）をカウント
        recent_errors = 0
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        
        for error in errors:
            if error.get("timestamp", "") >= one_hour_ago:
                recent_errors += 1
        
        # エラー率を計算（最大100%）
        return min(100.0, (recent_errors / len(logs)) * 100)
    
    def generate_server_status_chart(self) -> gr.Plot:
        """
        サーバー状態のチャートを生成
        
        Returns:
            Matplotlib図
        """
        try:
            # ダミーデータの作成（実際の実装では実データを使用）
            timestamps = []
            statuses = []
            
            # ログから接続状態の履歴を抽出
            logs = self.debugger.get_recent_logs(100)
            
            for log in logs:
                msg = log.get("message", "")
                timestamp = log.get("timestamp", "")
                
                if "Connected to MCP server" in msg:
                    timestamps.append(timestamp)
                    statuses.append(1)  # 接続中
                elif "connection_error" in msg or "Failed to connect" in msg:
                    timestamps.append(timestamp)
                    statuses.append(0)  # 接続エラー
            
            # チャートの作成
            fig, ax = plt.subplots(figsize=(10, 4))
            
            if timestamps and statuses:
                # 日時文字列をdatetimeオブジェクトに変換
                dt_timestamps = [datetime.fromisoformat(ts) for ts in timestamps]
                
                # プロット
                ax.plot(dt_timestamps, statuses, 'o-', color='blue')
                ax.set_yticks([0, 1])
                ax.set_yticklabels(['切断', '接続中'])
                ax.set_xlabel('時間')
                ax.set_title('MCPサーバー接続状態')
                ax.grid(True, alpha=0.3)
                
                # x軸の日時フォーマットを設定
                fig.autofmt_xdate()
            else:
                ax.text(0.5, 0.5, '接続データがありません', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=ax.transAxes)
                ax.set_xticks([])
                ax.set_yticks([])
            
            return fig
        except Exception as e:
            self.debugger.record_error(
                "chart_generation_error",
                f"Error generating server status chart: {str(e)}"
            )
            
            # エラー表示用の図を作成
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.text(0.5, 0.5, f'チャート生成エラー: {str(e)}', 
                    horizontalalignment='center', verticalalignment='center', 
                    transform=ax.transAxes, color='red')
            ax.set_xticks([])
            ax.set_yticks([])
            return fig
    
    def generate_tool_usage_chart(self) -> gr.Plot:
        """
        ツール使用状況のチャートを生成
        
        Returns:
            Matplotlib図
        """
        try:
            # ツール呼び出し回数のデータを使用
            calls = self.tool_stats.get("calls", {})
            
            # チャートの作成
            fig, ax = plt.subplots(figsize=(10, 5))
            
            if calls:
                # ツール名と呼び出し回数の取得
                tools = list(calls.keys())
                counts = list(calls.values())
                
                # 呼び出し回数に基づいてソート
                sorted_data = sorted(zip(tools, counts), key=lambda x: x[1], reverse=True)
                tools = [x[0] for x in sorted_data]
                counts = [x[1] for x in sorted_data]
                
                # 最大10個のツールに制限
                if len(tools) > 10:
                    tools = tools[:10]
                    counts = counts[:10]
                    tools[-1] = "その他"  # 最後のツールを「その他」に変更
                
                # 水平バーチャートの作成
                y_pos = np.arange(len(tools))
                ax.barh(y_pos, counts, align='center')
                ax.set_yticks(y_pos)
                ax.set_yticklabels(tools)
                ax.invert_yaxis()  # 最大値を上にする
                ax.set_xlabel('呼び出し回数')
                ax.set_title('ツール使用頻度')
                
                # 各バーに数値を表示
                for i, v in enumerate(counts):
                    ax.text(v + 0.1, i, str(v), va='center')
            else:
                ax.text(0.5, 0.5, 'ツール使用データがありません', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=ax.transAxes)
                ax.set_xticks([])
                ax.set_yticks([])
            
            return fig
        except Exception as e:
            self.debugger.record_error(
                "chart_generation_error",
                f"Error generating tool usage chart: {str(e)}"
            )
            
            # エラー表示用の図を作成
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.text(0.5, 0.5, f'チャート生成エラー: {str(e)}', 
                    horizontalalignment='center', verticalalignment='center', 
                    transform=ax.transAxes, color='red')
            ax.set_xticks([])
            ax.set_yticks([])
            return fig
    
    def generate_error_trend_chart(self) -> gr.Plot:
        """
        エラー傾向のチャートを生成
        
        Returns:
            Matplotlib図
        """
        try:
            # エラータイムラインのデータを使用
            timeline = self.error_stats.get("timeline", [])
            
            # チャートの作成
            fig, ax = plt.subplots(figsize=(10, 4))
            
            if timeline:
                # タイムスタンプを時間単位でグループ化
                timestamps = [datetime.fromisoformat(item["timestamp"]) for item in timeline]
                error_types = [item["type"] for item in timeline]
                
                # 最近24時間のエラーに限定
                now = datetime.now()
                recent_data = [(ts, et) for ts, et in zip(timestamps, error_types) 
                              if (now - ts).total_seconds() <= 24 * 3600]
                
                if recent_data:
                    timestamps, error_types = zip(*recent_data)
                else:
                    timestamps, error_types = [], []
                
                if timestamps and error_types:
                    # 時間ごとにエラーをカウント
                    hour_counts = {}
                    for ts, et in zip(timestamps, error_types):
                        hour_key = ts.replace(minute=0, second=0, microsecond=0)
                        if hour_key in hour_counts:
                            hour_counts[hour_key] += 1
                        else:
                            hour_counts[hour_key] = 1
                    
                    # プロット用のデータを作成
                    x = sorted(hour_counts.keys())
                    y = [hour_counts[k] for k in x]
                    
                    # プロット
                    ax.plot(x, y, 'o-', color='red')
                    ax.set_xlabel('時間')
                    ax.set_ylabel('エラー数')
                    ax.set_title('時間ごとのエラー数')
                    ax.grid(True, alpha=0.3)
                    
                    # x軸の日時フォーマットを設定
                    fig.autofmt_xdate()
                else:
                    ax.text(0.5, 0.5, '最近24時間のエラーデータがありません', 
                            horizontalalignment='center', verticalalignment='center',
                            transform=ax.transAxes)
                    ax.set_xticks([])
                    ax.set_yticks([])
            else:
                ax.text(0.5, 0.5, 'エラーデータがありません', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=ax.transAxes)
                ax.set_xticks([])
                ax.set_yticks([])
            
            return fig
        except Exception as e:
            self.debugger.record_error(
                "chart_generation_error",
                f"Error generating error trend chart: {str(e)}"
            )
            
            # エラー表示用の図を作成
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.text(0.5, 0.5, f'チャート生成エラー: {str(e)}', 
                    horizontalalignment='center', verticalalignment='center', 
                    transform=ax.transAxes, color='red')
            ax.set_xticks([])
            ax.set_yticks([])
            return fig
    
    def generate_performance_chart(self) -> gr.Plot:
        """
        パフォーマンスチャートを生成
        
        Returns:
            Matplotlib図
        """
        try:
            # ツールコールの実行時間データ
            tool_calls = self.debugger.get_tool_calls(50)
            
            # チャートの作成
            fig, ax = plt.subplots(figsize=(10, 4))
            
            if tool_calls:
                # タイムスタンプと実行時間を抽出
                timestamps = []
                durations = []
                
                for call in tool_calls:
                    timestamp = call.get("timestamp", "")
                    duration = call.get("duration", 0)
                    
                    if timestamp and duration is not None:
                        timestamps.append(datetime.fromisoformat(timestamp))
                        durations.append(duration)
                
                if timestamps and durations:
                    # 実行時間をミリ秒に変換
                    durations_ms = [d * 1000 for d in durations]
                    
                    # プロット
                    ax.plot(timestamps, durations_ms, 'o-', color='green')
                    ax.set_xlabel('時間')
                    ax.set_ylabel('実行時間 (ms)')
                    ax.set_title('ツール実行時間の推移')
                    ax.grid(True, alpha=0.3)
                    
                    # 移動平均を追加
                    if len(durations_ms) >= 5:
                        window_size = min(5, len(durations_ms))
                        moving_avg = []
                        for i in range(len(durations_ms) - window_size + 1):
                            window = durations_ms[i:i+window_size]
                            moving_avg.append(sum(window) / window_size)
                        
                        moving_avg_times = timestamps[window_size-1:]
                        ax.plot(moving_avg_times, moving_avg, 'r--', linewidth=2, label='5ポイント移動平均')
                        ax.legend()
                    
                    # x軸の日時フォーマットを設定
                    fig.autofmt_xdate()
                else:
                    ax.text(0.5, 0.5, '実行時間データがありません', 
                            horizontalalignment='center', verticalalignment='center',
                            transform=ax.transAxes)
                    ax.set_xticks([])
                    ax.set_yticks([])
            else:
                ax.text(0.5, 0.5, 'ツール実行データがありません', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=ax.transAxes)
                ax.set_xticks([])
                ax.set_yticks([])
            
            return fig
        except Exception as e:
            self.debugger.record_error(
                "chart_generation_error",
                f"Error generating performance chart: {str(e)}"
            )
            
            # エラー表示用の図を作成
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.text(0.5, 0.5, f'チャート生成エラー: {str(e)}', 
                    horizontalalignment='center', verticalalignment='center', 
                    transform=ax.transAxes, color='red')
            ax.set_xticks([])
            ax.set_yticks([])
            return fig
    
    def generate_error_distribution_chart(self) -> gr.Plot:
        """
        エラー分布チャートを生成
        
        Returns:
            Matplotlib図
        """
        try:
            # エラータイプごとの発生回数
            error_counts = self.error_stats.get("count", {})
            
            # チャートの作成
            fig, ax = plt.subplots(figsize=(10, 5))
            
            if error_counts:
                # エラータイプと発生回数の取得
                error_types = list(error_counts.keys())
                counts = list(error_counts.values())
                
                # 発生回数に基づいてソート
                sorted_data = sorted(zip(error_types, counts), key=lambda x: x[1], reverse=True)
                error_types = [x[0] for x in sorted_data]
                counts = [x[1] for x in sorted_data]
                
                # 最大8個のエラータイプに制限
                if len(error_types) > 8:
                    others_count = sum(counts[7:])
                    error_types = error_types[:7] + ["その他"]
                    counts = counts[:7] + [others_count]
                
                # 円グラフの作成
                ax.pie(counts, labels=error_types, autopct='%1.1f%%', startangle=90)
                ax.axis('equal')  # 円を綺麗に表示するため
                ax.set_title('エラータイプの分布')
            else:
                ax.text(0.5, 0.5, 'エラーデータがありません', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=ax.transAxes)
                ax.set_xticks([])
                ax.set_yticks([])
            
            return fig
        except Exception as e:
            self.debugger.record_error(
                "chart_generation_error",
                f"Error generating error distribution chart: {str(e)}"
            )
            
            # エラー表示用の図を作成
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.text(0.5, 0.5, f'チャート生成エラー: {str(e)}', 
                    horizontalalignment='center', verticalalignment='center', 
                    transform=ax.transAxes, color='red')
            ax.set_xticks([])
            ax.set_yticks([])
            return fig
    
    def generate_tool_success_chart(self) -> gr.Plot:
        """
        ツールの成功率チャートを生成
        
        Returns:
            Matplotlib図
        """
        try:
            # ツールごとの成功率データ
            success_rates = self.tool_stats.get("success", {})
            
            # チャートの作成
            fig, ax = plt.subplots(figsize=(10, 5))
            
            if success_rates:
                # ツール名と成功率の取得
                tools = list(success_rates.keys())
                rates = list(success_rates.values())
                
                # 成功率に基づいてソート
                sorted_data = sorted(zip(tools, rates), key=lambda x: x[1])
                tools = [x[0] for x in sorted_data]
                rates = [x[1] for x in sorted_data]
                
                # 最大10個のツールに制限
                if len(tools) > 10:
                    tools = tools[-10:]  # 上位10個を表示
                    rates = rates[-10:]
                
                # 水平バーチャートの作成
                y_pos = np.arange(len(tools))
                ax.barh(y_pos, rates, align='center')
                ax.set_yticks(y_pos)
                ax.set_yticklabels(tools)
                ax.set_xlabel('成功率 (%)')
                ax.set_title('ツール成功率')
                ax.set_xlim(0, 100)  # パーセンテージなので0-100
                
                # 各バーにパーセンテージを表示
                for i, v in enumerate(rates):
                    ax.text(v + 1, i, f'{v:.1f}%', va='center')
                
                # 警告ラインの追加（80%未満を警告色に）
                warning_level = 80
                ax.axvline(x=warning_level, color='r', linestyle='--', alpha=0.5)
            else:
                ax.text(0.5, 0.5, '成功率データがありません', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=ax.transAxes)
                ax.set_xticks([])
                ax.set_yticks([])
            
            return fig
        except Exception as e:
            self.debugger.record_error(
                "chart_generation_error",
                f"Error generating tool success chart: {str(e)}"
            )
            
            # エラー表示用の図を作成
# エラー表示用の図を作成
           fig, ax = plt.subplots(figsize=(8, 4))
           ax.text(0.5, 0.5, f'チャート生成エラー: {str(e)}', 
                   horizontalalignment='center', verticalalignment='center', 
                   transform=ax.transAxes, color='red')
           ax.set_xticks([])
           ax.set_yticks([])
           return fig
   
   def get_metrics_summary(self) -> Dict[str, Any]:
       """
       メトリクスの要約を取得
       
       Returns:
           メトリクスのサマリー情報
       """
       # ツール使用統計
       tool_calls = self.debugger.get_tool_calls(100)
       
       # エラー統計
       errors = self.debugger.get_errors(50)
       
       # 要約情報を作成
       summary = {
           "timestamp": datetime.now().isoformat(),
           "tool_metrics": {
               "total_calls": len(tool_calls),
               "unique_tools": len(self.tool_stats.get("calls", {})),
               "avg_duration_ms": sum(self.tool_stats.get("duration", {}).values()) / len(self.tool_stats.get("duration", {})) * 1000 if self.tool_stats.get("duration", {}) else 0,
               "avg_success_rate": sum(self.tool_stats.get("success", {}).values()) / len(self.tool_stats.get("success", {})) if self.tool_stats.get("success", {}) else 0
           },
           "error_metrics": {
               "total_errors": len(errors),
               "unique_error_types": len(self.error_stats.get("count", {})),
               "most_common_error": max(self.error_stats.get("count", {}).items(), key=lambda x: x[1])[0] if self.error_stats.get("count", {}) else "N/A",
               "most_common_source": max(self.error_stats.get("sources", {}).items(), key=lambda x: x[1])[0] if self.error_stats.get("sources", {}) else "N/A"
           }
       }
       
       return summary
   
   def get_tool_details_table(self) -> List[List[str]]:
       """
       ツール詳細テーブルデータを取得
       
       Returns:
           ツール詳細のテーブルデータ
       """
       try:
           # ツール統計データ
           calls = self.tool_stats.get("calls", {})
           durations = self.tool_stats.get("duration", {})
           success_rates = self.tool_stats.get("success", {})
           last_used = self.tool_stats.get("last_used", {})
           
           # テーブルのヘッダー行
           table = [["ツール名", "呼び出し回数", "平均実行時間(ms)", "成功率(%)", "最終使用時刻"]]
           
           # ツールごとの詳細
           for tool_name in calls.keys():
               call_count = calls.get(tool_name, 0)
               duration = durations.get(tool_name, 0) * 1000  # 秒をミリ秒に変換
               success_rate = success_rates.get(tool_name, 0)
               last_used_time = last_used.get(tool_name, "")
               
               # タイムスタンプを読みやすい形式に変換
               if last_used_time:
                   try:
                       dt = datetime.fromisoformat(last_used_time)
                       last_used_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                   except Exception:
                       pass  # 変換できない場合は元のまま
               
               # 行の追加
               table.append([
                   tool_name,
                   str(call_count),
                   f"{duration:.2f}",
                   f"{success_rate:.1f}",
                   last_used_time
               ])
           
           return table
       except Exception as e:
           self.debugger.record_error(
               "table_generation_error",
               f"Error generating tool details table: {str(e)}"
           )
           return [["Error generating table", str(e)]]
   
   def get_error_details_table(self) -> List[List[str]]:
       """
       エラー詳細テーブルデータを取得
       
       Returns:
           エラー詳細のテーブルデータ
       """
       try:
           # 最近のエラーを取得
           errors = self.debugger.get_errors(20)
           
           # テーブルのヘッダー行
           table = [["タイムスタンプ", "エラータイプ", "メッセージ", "発生源"]]
           
           # エラーごとの詳細
           for error in errors:
               timestamp = error.get("timestamp", "")
               error_type = error.get("type", "unknown")
               message = error.get("message", "")
               details = error.get("details", {})
               source = details.get("tool", "unknown") if isinstance(details, dict) else "unknown"
               
               # タイムスタンプを読みやすい形式に変換
               if timestamp:
                   try:
                       dt = datetime.fromisoformat(timestamp)
                       timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                   except Exception:
                       pass  # 変換できない場合は元のまま
               
               # メッセージが長すぎる場合は省略
               if len(message) > 100:
                   message = message[:97] + "..."
               
               # 行の追加
               table.append([
                   timestamp,
                   error_type,
                   message,
                   source
               ])
           
           return table
       except Exception as e:
           self.debugger.record_error(
               "table_generation_error",
               f"Error generating error details table: {str(e)}"
           )
           return [["Error generating table", str(e)]]

class MCPVisualizer:
   """
   MCPサーバー可視化コンポーネントの管理クラス
   
   主な責務:
   - 可視化モジュールのライフサイクル管理
   - Gradio UIコンポーネントの構築
   - 定期的なデータ更新
   """
   def __init__(self, debugger: AgnoMCPDebugger):
       """
       MCPVisualizer を初期化
       
       Args:
           debugger: AgnoMCPDebugger インスタンス
       """
       self.debugger = debugger
       self.server_visualizer = MCPServerVisualizer(debugger)
       self.update_interval = 10  # 秒
       self.last_metrics_update = time.time()
       
       self.debugger.log("MCPVisualizer initialized", "info")
   
   def build_metrics_dashboard(self) -> gr.Blocks:
       """
       メトリクスダッシュボードUI構築
       
       Returns:
           Gradio Blocks コンポーネント
       """
       with gr.Blocks() as dashboard:
           gr.Markdown("# MCP サーバーメトリクスダッシュボード")
           
           with gr.Row():
               with gr.Column():
                   gr.Markdown("## ツール使用統計")
                   tool_chart = gr.Plot(value=self.server_visualizer.generate_tool_usage_chart())
               
               with gr.Column():
                   gr.Markdown("## サーバー状態")
                   server_chart = gr.Plot(value=self.server_visualizer.generate_server_status_chart())
           
           with gr.Row():
               with gr.Column():
                   gr.Markdown("## エラー傾向")
                   error_chart = gr.Plot(value=self.server_visualizer.generate_error_trend_chart())
               
               with gr.Column():
                   gr.Markdown("## パフォーマンス指標")
                   perf_chart = gr.Plot(value=self.server_visualizer.generate_performance_chart())
           
           with gr.Row():
               with gr.Column():
                   gr.Markdown("## エラー分布")
                   error_dist_chart = gr.Plot(value=self.server_visualizer.generate_error_distribution_chart())
               
               with gr.Column():
                   gr.Markdown("## ツール成功率")
                   success_chart = gr.Plot(value=self.server_visualizer.generate_tool_success_chart())
           
           refresh_btn = gr.Button("更新")
           
           # 自動更新間隔の設定
           update_interval = gr.Slider(
               minimum=5,
               maximum=60,
               value=self.update_interval,
               step=5,
               label="自動更新間隔（秒）"
           )
           
           # 自動更新切り替え
           auto_update = gr.Checkbox(
               label="自動更新を有効化",
               value=True
           )
           
           # 更新ボタンのクリックイベント
           refresh_btn.click(
               fn=self.update_dashboard,
               inputs=[],
               outputs=[
                   tool_chart, server_chart, error_chart, 
                   perf_chart, error_dist_chart, success_chart
               ]
           )
           
           # 自動更新間隔変更イベント
           update_interval.change(
               fn=lambda interval: self.set_update_interval(interval),
               inputs=[update_interval],
               outputs=[]
           )
           
           # 自動更新の設定
           def setup_auto_update():
               tool_chart.every(
                   self.update_interval,
                   self.server_visualizer.generate_tool_usage_chart,
                   inputs=None,
                   outputs=tool_chart,
                   show_progress=False
               )
               server_chart.every(
                   self.update_interval,
                   self.server_visualizer.generate_server_status_chart,
                   inputs=None,
                   outputs=server_chart,
                   show_progress=False
               )
               error_chart.every(
                   self.update_interval,
                   self.server_visualizer.generate_error_trend_chart,
                   inputs=None,
                   outputs=error_chart,
                   show_progress=False
               )
               perf_chart.every(
                   self.update_interval,
                   self.server_visualizer.generate_performance_chart,
                   inputs=None,
                   outputs=perf_chart,
                   show_progress=False
               )
               error_dist_chart.every(
                   self.update_interval,
                   self.server_visualizer.generate_error_distribution_chart,
                   inputs=None,
                   outputs=error_dist_chart,
                   show_progress=False
               )
               success_chart.every(
                   self.update_interval,
                   self.server_visualizer.generate_tool_success_chart,
                   inputs=None,
                   outputs=success_chart,
                   show_progress=False
               )
           
           # 自動更新トグルイベント
           auto_update.change(
               fn=lambda value: self.toggle_auto_update(value, setup_auto_update),
               inputs=[auto_update],
               outputs=[]
           )
           
           # 初期セットアップ
           if auto_update.value:
               setup_auto_update()
       
       return dashboard
   
   def build_details_dashboard(self) -> gr.Blocks:
       """
       詳細ダッシュボードUI構築
       
       Returns:
           Gradio Blocks コンポーネント
       """
       with gr.Blocks() as details:
           gr.Markdown("# MCP サーバー詳細情報")
           
           with gr.Tabs():
               with gr.Tab("ツール詳細"):
                   tool_details_table = gr.Dataframe(
                       value=self.server_visualizer.get_tool_details_table(),
                       headers=["ツール名", "呼び出し回数", "平均実行時間(ms)", "成功率(%)", "最終使用時刻"],
                       datatype=["str", "str", "str", "str", "str"],
                       col_count=(5, "fixed")
                   )
                   
                   tool_details_refresh = gr.Button("更新")
                   
                   tool_details_refresh.click(
                       fn=self.server_visualizer.get_tool_details_table,
                       inputs=[],
                       outputs=[tool_details_table]
                   )
               
               with gr.Tab("エラー詳細"):
                   error_details_table = gr.Dataframe(
                       value=self.server_visualizer.get_error_details_table(),
                       headers=["タイムスタンプ", "エラータイプ", "メッセージ", "発生源"],
                       datatype=["str", "str", "str", "str"],
                       col_count=(4, "fixed")
                   )
                   
                   error_details_refresh = gr.Button("更新")
                   
                   error_details_refresh.click(
                       fn=self.server_visualizer.get_error_details_table,
                       inputs=[],
                       outputs=[error_details_table]
                   )
               
               with gr.Tab("メトリクスサマリー"):
                   metrics_summary = gr.JSON(value=self.server_visualizer.get_metrics_summary())
                   
                   metrics_summary_refresh = gr.Button("更新")
                   
                   metrics_summary_refresh.click(
                       fn=self.server_visualizer.get_metrics_summary,
                       inputs=[],
                       outputs=[metrics_summary]
                   )
       
       return details
   
   async def update_metrics(self) -> Dict[str, Any]:
       """
       メトリクスの更新
       
       Returns:
           更新されたメトリクス
       """
       return await self.server_visualizer.update_metrics()
   
   def update_dashboard(self) -> Tuple[gr.Plot, gr.Plot, gr.Plot, gr.Plot, gr.Plot, gr.Plot]:
       """
       ダッシュボードを更新
       
       Returns:
           更新されたチャートのタプル
       """
       try:
           # メトリクスの更新（非同期ではないバージョン）
           current_time = time.time()
           if current_time - self.last_metrics_update >= self.update_interval:
               # この部分は非同期なので、実際にはイベントループで実行する必要がある
               # しかし、Gradioの関数は同期的なので、実際のメトリクス更新は
               # チャート生成時に内部で行われる
               self.last_metrics_update = current_time
           
           # 各チャートを生成
           tool_chart = self.server_visualizer.generate_tool_usage_chart()
           server_chart = self.server_visualizer.generate_server_status_chart()
           error_chart = self.server_visualizer.generate_error_trend_chart()
           perf_chart = self.server_visualizer.generate_performance_chart()
           error_dist_chart = self.server_visualizer.generate_error_distribution_chart()
           success_chart = self.server_visualizer.generate_tool_success_chart()
           
           return tool_chart, server_chart, error_chart, perf_chart, error_dist_chart, success_chart
       except Exception as e:
           self.debugger.record_error(
               "dashboard_update_error",
               f"Error updating dashboard: {str(e)}"
           )
           
           # エラー発生時は空のプロットを返す
           error_fig, ax = plt.subplots(figsize=(8, 4))
           ax.text(0.5, 0.5, f'ダッシュボード更新エラー: {str(e)}', 
                   horizontalalignment='center', verticalalignment='center', 
                   transform=ax.transAxes, color='red')
           ax.set_xticks([])
           ax.set_yticks([])
           
           # すべてのチャートに同じエラーメッセージを表示
           return error_fig, error_fig, error_fig, error_fig, error_fig, error_fig
   
   def set_update_interval(self, interval: float) -> None:
       """
       自動更新間隔を設定
       
       Args:
           interval: 更新間隔（秒）
       """
       self.update_interval = interval
       self.debugger.log(f"Update interval set to {interval} seconds", "info")
   
   def toggle_auto_update(self, enabled: bool, setup_fn: callable) -> None:
       """
       自動更新を切り替え
       
       Args:
           enabled: 有効化するかどうか
           setup_fn: 自動更新設定関数
       """
       if enabled:
           setup_fn()
           self.debugger.log("Auto update enabled", "info")
       else:
           # 実際のGradioアプリでは自動更新を無効化するコードが必要
           self.debugger.log("Auto update disabled", "info")
   
   def build_visualization_tab(self) -> gr.Tab:
       """
       可視化タブを構築
       
       Returns:
           Gradio Tab コンポーネント
       """
       with gr.Tab("可視化") as tab:
           with gr.Tabs():
               with gr.Tab("メトリクスダッシュボード"):
                   dashboard = self.build_metrics_dashboard()
               
               with gr.Tab("詳細情報"):
                   details = self.build_details_dashboard()
       
       return tab
   
   
# ollama_mcp/visualizer.py に追加

def get_visualization_css() -> str:
    """
    可視化コンポーネント用のCSSスタイルを取得
    
    Returns:
        CSSスタイル文字列
    """
    return """
    .visualization-container {
        padding: 10px;
        background-color: #f8f9fa;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    }
    
    .chart-container {
        background-color: white;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    .metric-card {
        background-color: white;
        padding: 15px;
        border-radius: 5px;
        margin: 5px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        margin: 10px 0;
    }
    
    .metric-label {
        font-size: 14px;
        color: #666;
    }
    
    .tab-header {
        font-size: 18px;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 1px solid #eee;
    }
    
    .success-value {
        color: #28a745;
    }
    
    .warning-value {
        color: #ffc107;
    }
    
    .error-value {
        color: #dc3545;
    }
    """