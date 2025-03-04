from typing import Dict, Any
from loguru import logger
import os
import json
from datetime import datetime

# ログファイルのディレクトリ
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ログファイル名設定
log_file = f"{LOG_DIR}/mcp_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# ロガー設定
logger.add(log_file, rotation="10 MB", level="DEBUG")

def log_request_response(
    server_name: str,
    tool_name: str,
    arguments: Dict[str, Any],
    response: Dict[str, Any],
    is_error: bool = False
) -> Dict[str, Any]:
    """リクエストとレスポンスをログに記録"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "server": server_name,
        "tool": tool_name,
        "arguments": arguments,
        "response": response,
        "is_error": is_error
    }
    
    # 人間可読形式とJSON形式の両方でログを残す
    logger.info(f"MCP REQUEST: {server_name}/{tool_name} - ARGS: {json.dumps(arguments)}")
    if is_error:
        logger.error(f"MCP ERROR RESPONSE: {response}")
    else:
        logger.info(f"MCP RESPONSE: {json.dumps(response)}")
    
    # 構造化されたJSONとしても記録
    logger.debug(json.dumps(log_entry))
    
    return log_entry 