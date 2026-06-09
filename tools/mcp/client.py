"""MCP 客户端 — 连接外部 MCP Server 并加载工具（基于 FastMCP 3.x）

通过后台线程维护与 MCP Server 的长连接，对外暴露同步接口。
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from tools.builtins import Tool


class MCPBridge:
    """持久 MCP 连接桥 — 后台线程运行 event loop，对外提供同步 API"""

    def __init__(self) -> None:
        self._client: Client | None = None
        self._tools: list[dict] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._error: Exception | None = None

    # ------------------------------------------------------------------
    # 公开 API（同步）
    # ------------------------------------------------------------------

    def connect(self, command: str, args: list[str] | None = None) -> list[dict]:
        """同步连接到 MCP 服务器，返回工具列表"""
        self._ready.clear()
        self._error = None
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(command, args or []),
            daemon=True,
        )
        self._thread.start()

        # 等待连接完成或出错
        self._ready.wait(timeout=30)
        if self._error:
            raise self._error
        if not self._ready.is_set():
            raise RuntimeError("MCP connection timed out")
        return self._tools

    @property
    def tools(self) -> list[dict]:
        return self._tools

    def call_tool(self, name: str, arguments: dict) -> str:
        """同步调用 MCP 工具"""
        if not self._loop or not self._loop.is_running():
            raise RuntimeError("MCP connection is closed")

        future = asyncio.run_coroutine_threadsafe(
            self._call_tool_async(name, arguments),
            self._loop,
        )
        result = future.result(timeout=60)

        if hasattr(result, 'data') and result.data is not None:
            return str(result.data)
        if hasattr(result, 'content'):
            contents = result.content
            if contents:
                return "\n".join(
                    c.text if hasattr(c, 'text') else str(c)
                    for c in contents
                )
        return str(result)

    def close(self) -> None:
        """关闭连接"""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._close(), self._loop)
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)

    # ------------------------------------------------------------------
    # 内部实现（异步，运行在后台线程的 event loop 中）
    # ------------------------------------------------------------------

    def _run_loop(self, command: str, args: list[str]) -> None:
        """后台线程入口：创建 event loop 并运行"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect(command, args))
            self._ready.set()
            # 保持 event loop 运行，等待后续工具调用
            self._loop.run_forever()
        except Exception as e:
            self._error = e
            self._ready.set()

    async def _connect(self, command: str, args: list[str]) -> None:
        transport = StdioTransport(command, args)
        self._client = Client(transport)
        await self._client.__aenter__()

        tools_result = await self._client.list_tools()
        self._tools = [
            {
                "name": t.name,
                "description": t.description or "",
                "inputSchema": t.inputSchema if hasattr(t, "inputSchema") else {},
            }
            for t in tools_result
        ]

    async def _call_tool_async(self, name: str, arguments: dict) -> Any:
        if not self._client:
            raise RuntimeError("Not connected to MCP server")
        return await self._client.call_tool(name, arguments)

    async def _close(self) -> None:
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None


def load_mcp_tools(bridge: MCPBridge) -> list[Tool]:
    """将 MCP 工具列表包装为内置 Tool 对象"""
    wrapped = []
    for mt in bridge.tools:
        name = mt["name"]

        def make_fn(tool_name):
            def fn(**kwargs):
                return bridge.call_tool(tool_name, kwargs)
            return fn

        params = mt.get("inputSchema", {})
        if "properties" not in params:
            params = {"type": "object", "properties": {}}

        wrapped.append(Tool(
            name=f"mcp_{name}",
            description=mt.get("description", f"MCP tool: {name}"),
            parameters=params,
            fn=make_fn(name),
        ))

    return wrapped
