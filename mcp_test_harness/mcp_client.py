from typing import List, Dict, Any
from mcp import ClientSession, types
from mcp.client.stdio import stdio_client
from .logger import logger, log_request_response
from .models import Tool, ToolResponse
import asyncio
import json

async def list_server_tools(server_name: str, server_param: Any) -> List[Tool]:
    """MCPサーバーの利用可能なツールを一覧表示"""
    try:
        print(f"🔍 Starting list_server_tools for {server_name}")
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
                
                tools = getattr(tools_response, 'tools', [])
                if tools:
                    print(f"🔍 tools attribute found: {tools}")
                    tools = [
                        Tool(
                            name=tool.name,
                            description=tool.description,
                            schema=json.dumps(tool.inputSchema, indent=2)
                        )
                        for tool in tools
                    ]
                else:
                    print(f"❌ No tools attribute in response from {server_name}")
                    logger.error(f"No tools attribute in response from {server_name}")
                    return []
                
                print(f"✅ Listed {len(tools)} tools from {server_name}")
                logger.info(f"Listed {len(tools)} tools from {server_name}")
                return tools
    except Exception as e:
        error_msg = f"Error listing tools from {server_name}: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)
        return []

async def call_server_tool(
    server_name: str,
    server_param: Any,
    tool_name: str,
    arguments: Dict[str, Any]
) -> ToolResponse:
    """MCPサーバーのツールを呼び出す"""
    try:
        print(f"🔍 Starting call_server_tool for {tool_name} on {server_name}")
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
                
                content = getattr(result, 'content', None)
                if content is not None:
                    print(f"🔍 content attribute found: {content}")
                    response_data = content if isinstance(content, dict) else {"data": content}
                else:
                    print("🔍 No content attribute, using raw result")
                    response_data = {"data": result}
                
                print(f"📝 Response data: {response_data}")
                
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