from typing import List, Dict, Any, Optional
from mcp import ClientSession, types
from mcp.client.stdio import stdio_client
from .logger import logger, log_request_response
from .models import Tool, ToolResponse
import asyncio
import json

async def list_server_tools(
    server_name: str, 
    server_param: Any,
    _test_session: Optional[ClientSession] = None,
    _test_tools_response: Optional[Any] = None
) -> List[Tool]:
    """MCPサーバーの利用可能なツールを一覧表示"""
    try:
        print(f"🔍 Starting list_server_tools for {server_name}")
        if _test_session and _test_tools_response:
            # テスト用パス
            print("🔍 Using test session and response")
            session = _test_session
            tools_response = _test_tools_response
        else:
            # 通常のパス
            async with stdio_client(server_param) as (read, write):
                print("📡 Connected to stdio_client")
                async with ClientSession(read, write) as session:
                    print("🤝 Initializing session")
                    await session.initialize()
                    print("📋 Requesting tools list")
                    tools_response = await session.list_tools()
        
        print(f"📦 Received tools_response: {tools_response}")
        print(f"🔍 tools_response type: {type(tools_response)}")
        print(f"🔍 tools_response dir: {dir(tools_response)}")
        
        # モックオブジェクトの属性を正しく取得
        tools = getattr(tools_response, 'tools', [])
        if not tools:
            print(f"❌ No tools attribute in response from {server_name}")
            logger.error(f"No tools attribute in response from {server_name}")
            return []
        
        print(f"🔍 tools attribute found: {tools}")
        try:
            converted_tools = []
            for tool in tools:
                try:
                    # ツールの属性を取得
                    name = getattr(tool, 'name', None)
                    description = getattr(tool, 'description', None)
                    input_schema = getattr(tool, 'inputSchema', None)
                    
                    if not all([name, description, input_schema]):
                        error_msg = f"Missing required attributes in tool: {tool}"
                        logger.error(error_msg)
                        print(f"❌ {error_msg}")
                        continue
                    
                    # ツールオブジェクトを作成
                    converted_tool = Tool(
                        name=name,
                        description=description,
                        schema=json.dumps(input_schema, indent=2)
                    )
                    converted_tools.append(converted_tool)
                except Exception as e:
                    error_msg = f"Error converting tool {tool}: {str(e)}"
                    logger.error(error_msg)
                    print(f"❌ {error_msg}")
                    continue
            
            print(f"✅ Converted {len(converted_tools)} tools")
            return converted_tools
        except Exception as e:
            error_msg = f"Error converting tools: {str(e)}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            return []
            
    except Exception as e:
        error_msg = f"Error listing tools from {server_name}: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)
        return []

async def call_server_tool(
    server_name: str,
    server_param: Any,
    tool_name: str,
    arguments: Dict[str, Any],
    _test_session: Optional[ClientSession] = None,
    _test_result: Optional[Any] = None
) -> ToolResponse:
    """MCPサーバーのツールを呼び出す"""
    try:
        print(f"🔍 Starting call_server_tool for {tool_name} on {server_name}")
        if _test_session and _test_result:
            # テスト用パス
            print("🔍 Using test session and result")
            session = _test_session
            result = _test_result
        else:
            # 通常のパス
            async with stdio_client(server_param) as (read, write):
                print("📡 Connected to stdio_client")
                async with ClientSession(read, write) as session:
                    print("🤝 Initializing session")
                    await session.initialize()
                    print(f"🛠️ Calling tool {tool_name} with arguments: {arguments}")
                    result = await session.call_tool(tool_name, arguments=arguments)
        
        print(f"📦 Received result: {result}")
        print(f"🔍 result type: {type(result)}")
        print(f"🔍 result dir: {dir(result)}")
        
        # モックオブジェクトの属性を正しく取得
        content = getattr(result, 'content', None)
        if content is not None:
            print(f"🔍 content attribute found: {content}")
            response_data = content if isinstance(content, dict) else {"data": content}
        else:
            print("🔍 No content attribute, using raw result")
            response_data = {"data": result}
        
        print(f"📝 Response data: {response_data}")
        
        # モックオブジェクトの属性を正しく取得
        is_error = getattr(result, 'isError', False)
        print(f"❌ is_error: {is_error}")
        print(f"🔍 is_error type: {type(is_error)}")
        
        log_entry = log_request_response(
            server_name, 
            tool_name, 
            arguments, 
            response_data, 
            is_error=is_error
        )
        print(f"📋 Log entry: {log_entry}")
        
        success = not is_error
        print(f"✅ Success status: {success}")
        
        return ToolResponse(
            success=success,
            result=response_data,
            log_entry=log_entry
        )
    except Exception as e:
        error_msg = f"Error calling tool {tool_name} on {server_name}: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)
        log_entry = log_request_response(
            server_name, 
            tool_name, 
            arguments, 
            {"error": str(e)}, 
            is_error=True
        )
        return ToolResponse(
            success=False,
            error=str(e),
            log_entry=log_entry
        ) 