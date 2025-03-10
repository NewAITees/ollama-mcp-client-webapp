from typing import Dict, Any, Optional
import json
import os
from mcp import StdioServerParameters
from .logger import logger
from .models import ServerConfig

def convert_windows_path_to_wsl(windows_path: str) -> str:
    """WindowsのパスをWSLのパスに変換"""
    # Windowsのパスを正規化
    windows_path = windows_path.replace('\\', '/')
    
    # C:ドライブの場合
    if windows_path.startswith('C:/'):
        return f"/mnt/c{windows_path[2:]}"
    
    # その他のドライブの場合
    if ':' in windows_path:
        drive_letter = windows_path[0]
        return f"/mnt/{drive_letter.lower()}{windows_path[2:]}"
    
    return windows_path

def load_server_config(config_path: str = "config/servers.json") -> Dict[str, Any]:
    """サーバー設定ファイルを読み込む"""
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        raise FileNotFoundError(f"Config file not found: {config_path}")
        
    try:
        with open(config_path, 'r') as f:
            config: Dict[str, Any] = json.load(f)
        logger.info(f"Loaded server config from {config_path}")
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load server config: {e}")
        raise

def create_server_parameters(config: Dict[str, Any]) -> Dict[str, StdioServerParameters]:
    """サーバー設定からStdioServerParametersを作成"""
    server_parameters: Dict[str, StdioServerParameters] = {}
    
    for server_name, server_config in config["mcpServers"].items():
        env_vars: Dict[str, str] = {}
        if "env" in server_config:
            for key, value in server_config["env"].items():
                # 空の値は環境変数から取得
                if value == "" and key in os.environ:
                    env_value = os.environ.get(key)
                    if env_value is not None:
                        env_vars[key] = env_value
                else:
                    env_vars[key] = str(value)
        
        # PATHを環境変数に追加
        path_value = os.environ.get("PATH")
        if path_value is not None:
            env_vars["PATH"] = path_value
        
        # Windowsネイティブコマンドかどうかをチェック
        is_windows_native = server_config["command"] in ["node", "cmd", "powershell", "cmd.exe", "powershell.exe"]
        
        # コマンド引数のパスを変換
        args = server_config.get("args", [])
        converted_args = []
        for arg in args:
            if isinstance(arg, str) and ('/' in arg or '\\' in arg) and not is_windows_native:
                converted_args.append(convert_windows_path_to_wsl(arg))
            else:
                converted_args.append(arg)
        
        server_parameter = StdioServerParameters(
            command=server_config["command"],
            args=converted_args,
            env=env_vars
        )
        
        server_parameters[server_name] = server_parameter
        logger.info(f"Created server parameters for {server_name}")
    
    return server_parameters 