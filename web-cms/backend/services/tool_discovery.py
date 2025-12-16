"""
Tool Discovery service.

Handles discovering tools from MCP servers via stdio protocol.
"""

import json
import os
import subprocess
import sys

from backend.config import TOOLS_CACHE_PATH, logger


def discover_tools_for_server(server_name: str, server_config: dict) -> list:
    """Start MCP server process temporarily, query tools via stdio, and cache them."""
    if server_config.get("disabled"):
        logger.info(f"[{server_name}] Skipping tool discovery - server is disabled")
        return []
    
    server_type = server_config.get("type", "stdio")
    
    try:
        if server_type == "stdio":
            command = server_config.get("command")
            args = server_config.get("args", [])
            if not command:
                logger.error(f"[{server_name}] Missing 'command' in config")
                return []
            cmd = [command] + args
        elif server_type in ("http", "sse", "streamablehttp"):
            url = server_config.get("url")
            if not url:
                logger.error(f"[{server_name}] Missing 'url' for HTTP type server")
                return []
            cmd = [sys.executable, "-m", "mcp_proxy"]
            if server_type in ("http", "streamablehttp"):
                cmd += ["--transport", "streamablehttp"]
            headers = server_config.get("headers", {})
            for hk, hv in headers.items():
                cmd += ["-H", hk, str(hv)]
            cmd.append(url)
        else:
            logger.error(f"[{server_name}] Unsupported server type: {server_type}")
            return []
    except Exception as e:
        logger.error(f"[{server_name}] Error building command: {e}")
        return []
    
    child_env = os.environ.copy()
    for k, v in server_config.get("env", {}).items():
        child_env[str(k)] = str(v)
    
    process = None
    tools = []
    
    try:
        logger.info(f"[{server_name}] Starting process for tool discovery: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            text=True,
            env=child_env,
        )
        
        init_request = {
            "jsonrpc": "2.0",
            "id": "cms_init",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "MCP CMS Tool Discovery", "version": "1.0.0"}
            }
        }
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        init_response_line = process.stdout.readline()
        if not init_response_line:
            logger.error(f"[{server_name}] No response to initialize request")
            return []
        
        try:
            init_response = json.loads(init_response_line)
            if "error" in init_response:
                logger.error(f"[{server_name}] Initialize error: {init_response['error']}")
                return []
            logger.info(f"[{server_name}] Initialize successful")
        except json.JSONDecodeError:
            logger.error(f"[{server_name}] Invalid JSON in initialize response")
            return []
        
        tools_request = {
            "jsonrpc": "2.0",
            "id": "cms_tools_list",
            "method": "tools/list",
            "params": {}
        }
        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()
        
        tools_response_line = process.stdout.readline()
        if not tools_response_line:
            logger.error(f"[{server_name}] No response to tools/list request")
            return []
        
        try:
            tools_response = json.loads(tools_response_line)
            if "error" in tools_response:
                logger.error(f"[{server_name}] tools/list error: {tools_response['error']}")
                return []
            
            tools = tools_response.get("result", {}).get("tools", [])
            logger.info(f"[{server_name}] Discovered {len(tools)} tools")
        except json.JSONDecodeError:
            logger.error(f"[{server_name}] Invalid JSON in tools/list response")
            return []
        
        if tools:
            try:
                cache = {}
                if TOOLS_CACHE_PATH.exists():
                    with open(TOOLS_CACHE_PATH, 'r') as f:
                        cache = json.load(f)
                
                cache[server_name] = tools
                
                with open(TOOLS_CACHE_PATH, 'w') as f:
                    json.dump(cache, f, indent=2, ensure_ascii=False)
                
                logger.info(f"[{server_name}] Cached {len(tools)} tools for CMS")
            except Exception as e:
                logger.error(f"[{server_name}] Failed to cache tools: {e}")
        
        return tools
        
    except Exception as e:
        logger.error(f"[{server_name}] Tool discovery failed: {e}")
        return []
    
    finally:
        if process is not None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception:
                pass
            logger.info(f"[{server_name}] Process terminated")
