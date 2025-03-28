"""
Agnoを使用したMCPサーバー向けデバッグとログユーティリティ
"""
import json
import time
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
import asyncio
from datetime import datetime

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class AgnoMCPDebugger:
    """
    Agno MCPデバッグユーティリティ
    
    主な責務:
    - 詳細なログ記録
    - ツールコールのトレース
    - エラー診断
    - 会話履歴の保存と分析
    """
    def __init__(self, level: str = "info", log_dir: str = "logs"):
        """
        AgnoMCPDebuggerを初期化
        
        Args:
            level: ログレベル (debug, info, warning, error)
            log_dir: ログディレクトリのパス
        """
        self.level = level
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # ログファイルの設定
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"agno_mcp_{timestamp}.log"
        
        # ロギングの設定
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format='%(levelname)s    %(name)s:%(filename)s:%(lineno)d %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("agno-mcp")
        
        # メモリ内のログ管理
        self.logs: List[Dict[str, Any]] = []
        self.tool_calls: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        
        # メモリ制限
        self.max_logs = 100
        self.max_tool_calls = 50
        self.max_errors = 50
        
        # ログファイルのサイズ制限（1MB）
        self.max_log_size = 1024 * 1024
        
        self.logger.info(f"Initialized AgnoMCPDebugger at level {level}")
    
    def log(self, message: str, level: str = "info", data: Optional[Dict] = None) -> None:
        """
        メッセージを記録
        
        Args:
            message: ログメッセージ
            level: ログレベル
            data: 関連するデータ
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "data": data or {}
        }
        
        # メモリ内のログを管理
        self.logs.append(log_entry)
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        
        # ログファイルのサイズをチェック
        if self.log_file.exists() and self.log_file.stat().st_size > self.max_log_size:
            self._rotate_log_file()
        
        # ログレベルに応じて記録
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message)
    
    def record_tool_call(self, tool: str, args: Dict, result: Any, duration: float) -> None:
        """
        ツールコールを記録
        
        Args:
            tool: ツール名
            args: 引数
            result: 結果
            duration: 実行時間（秒）
        """
        tool_call = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool,
            "args": args,
            "result": result,
            "duration": duration
        }
        
        self.tool_calls.append(tool_call)
        if len(self.tool_calls) > self.max_tool_calls:
            self.tool_calls = self.tool_calls[-self.max_tool_calls:]
        
        # ツールコールはログに記録しない
    
    def record_error(self, error_type: str, message: str, details: Optional[Dict] = None) -> None:
        """
        エラーを記録
        
        Args:
            error_type: エラータイプ
            message: エラーメッセージ
            details: 詳細情報
        """
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": message,
            "details": details or {}
        }
        
        self.errors.append(error_entry)
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
        
        # エラーはログに記録
        self.log(f"Error: {error_type} - {message}", "error")
    
    def get_recent_logs(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        最近のログを取得
        
        Args:
            count: 取得するログの数
            
        Returns:
            ログエントリのリスト
        """
        return self.logs[-count:]
    
    def get_tool_calls(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        ツールコールを取得
        
        Args:
            count: 取得するツールコールの数
            
        Returns:
            ツールコールのリスト
        """
        return self.tool_calls[-count:]
    
    def get_errors(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        エラーを取得
        
        Args:
            count: 取得するエラーの数
            
        Returns:
            エラーのリスト
        """
        return self.errors[-count:]
    
    def export_logs(self, filepath: str) -> None:
        """
        ログをJSONファイルにエクスポート
        
        Args:
            filepath: エクスポート先のファイルパス
        """
        export_data = {
            "logs": self.logs,
            "tool_calls": self.tool_calls,
            "errors": self.errors,
            "exported_at": datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def clear_logs(self) -> None:
        """メモリ内ログをクリア"""
        self.logs = []
        self.log("Cleared memory logs", "info")
    
    def clear_tool_calls(self) -> None:
        """ツールコール履歴をクリア"""
        self.tool_calls = []
        self.log("Cleared tool calls", "info")
    
    def clear_errors(self) -> None:
        """エラー履歴をクリア"""
        self.errors = []
        self.log("Cleared errors", "info")
    
    def _rotate_log_file(self) -> None:
        """ログファイルをローテーション"""
        if not self.log_file.exists():
            return
            
        # 既存のログファイルをバックアップ
        backup_file = self.log_file.with_suffix(f".log.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.log_file.rename(backup_file)
        
        # 新しいログファイルを作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"agno_mcp_{timestamp}.log"
        
        # ロギングハンドラを更新
        for handler in self.logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                self.logger.removeHandler(handler)
        
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(logging.Formatter('%(levelname)s    %(name)s:%(filename)s:%(lineno)d %(message)s'))
        self.logger.addHandler(file_handler)
        
        self.log("Rotated log file", "info")

class ToolCallTracer:
    """
    ツールコールのトレース機能
    
    主な責務:
    - ツールコールの開始と終了を記録
    - 実行時間の計測
    - デバッガーへの記録
    """
    def __init__(self, debugger: AgnoMCPDebugger):
        """
        ToolCallTracerを初期化
        
        Args:
            debugger: デバッガー
        """
        self.debugger = debugger
    
    async def trace_tool_call(self, tool_func: Callable, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        ツールコールをトレース
        
        Args:
            tool_func: 実行するツール関数
            tool_name: ツール名
            args: 引数
            
        Returns:
            ツール実行結果
        """
        start_time = time.time()
        
        try:
            # ツール実行前にログ
            self.debugger.log(f"Executing tool: {tool_name}", "debug", {"args": args})
            
            # ツールを実行
            result = await tool_func(**args)
            
            # 実行時間を計算
            duration = time.time() - start_time
            
            # 結果を記録
            self.debugger.record_tool_call(tool_name, args, result, duration)
            
            return result
        except Exception as e:
            # エラーを記録
            duration = time.time() - start_time
            self.debugger.record_error(
                "tool_execution_error",
                f"Error executing tool {tool_name}: {str(e)}",
                {"tool": tool_name, "args": args, "error": str(e), "duration": duration}
            )
            raise 