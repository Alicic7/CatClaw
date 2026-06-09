"""CatClaw — 目标驱动的自主 AI Agent（记忆持久化 + MCP 扩展）"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Tuple

# 强制 stdout 使用 UTF-8，避免 emoji 在 GBK 终端上报编码错误
sys.stdout.reconfigure(encoding="utf-8")

from core.llm import call_llm
from core.memory import Memory
from core.node import Node, Flow, shared
from tools import get_tools, Tool, ToolExecutor

SYSTEM_PROMPT = (
    "你是一个会调用工具的助手。"
    "当问题涉及最新信息、模型版本、产品发布时间或事实核验时，优先先调用 search 工具，再基于搜索结果回答。"
    "若问题是本地文件/代码相关，优先使用 read/grep/find/ls 等本地工具。"
    "如果一轮回复中既需要向用户展示文字又需要继续调用工具，可以同时返回 content 和 tool_calls。"
)


@dataclass
class GoalState:
    """教学版 goal 状态：只保留最核心的字段。"""

    text: str | None = None
    active: bool = False


def goal_message(goal: GoalState) -> dict[str, str]:
    """创建写入历史的 goal 提醒消息。"""
    return {
        "role": "user",
        "content": (
            "Complete this goal fully:\n\n"
            f"{goal.text}\n\n"
            "Treat the goal text above as the whole task. Do not infer extra file, code, "
            "or project work unless the goal explicitly asks for it. Do not stop at only "
            "a plan, partial progress, or suggested next steps. Use tools only when the "
            "goal explicitly requires them. If this is a simple chat goal, reply directly. "
            "When the goal is fully complete and verified, call goal_complete."
        ),
    }


class ChatNode(Node):
    """调用 LLM，打印 assistant content，按 tool_calls 决定 agent loop 是否继续。"""

    def exec(self, payload: Any) -> Tuple[str, Any]:
        memory: Memory = shared["memory"]

        # build_context 已将 system_prompt 和长期记忆嵌入 messages，不再单独传 system_prompt
        messages = memory.build_context(system_prompt=SYSTEM_PROMPT)

        assistant_message = call_llm(
            messages=messages,
            tools=shared["tools"],
        )
        memory.add_message(assistant_message)

        content = assistant_message["content"]
        tool_calls = assistant_message.get("tool_calls")

        if content:
            print(f"\n🐱 CatClaw: {content}\n")

        if tool_calls:
            return "tool_call", assistant_message

        return "done", assistant_message


class ToolCallNode(Node):
    """执行 LLM 返回的 tool_calls。"""

    def exec(self, payload: Any) -> Tuple[str, Any]:
        response = payload
        memory: Memory = shared["memory"]
        executor: ToolExecutor = shared["tool_executor"]

        tool_calls = executor.parse_tool_calls(response)
        results = executor.execute_all(tool_calls)

        for tc, result in zip(tool_calls, results):
            print(f"  [Tool] 执行: {tc.name}({tc.arguments})")
            print(f"  [Tool] 结果: {result.content[:100]}...")
            memory.add_message(result.to_message())

        return "chat", None


def make_goal_complete_tool(goal: GoalState) -> Tool:
    """创建 goal_complete 工具。"""

    def goal_complete() -> str:
        if not goal.active:
            return "No active goal"
        goal.text = None
        goal.active = False
        return "Goal complete"

    return Tool(
        name="goal_complete",
        description=(
            "Mark the active goal as complete. "
            "Only call this after the goal is fully finished and verified. "
            "If no goal is active, this tool does nothing."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
        fn=goal_complete,
    )


def run_goal(flow: Flow, goal: GoalState) -> None:
    """一直运行 agent loop，直到 goal_complete 把 goal.active 改成 False。"""
    memory: Memory = shared["memory"]
    while goal.active:
        memory.add_message(goal_message(goal))
        flow.run(None)


def _load_mcp_tools() -> tuple[list[Tool], object | None]:
    """尝试从环境变量加载 MCP 工具。返回 (tools, bridge)。"""
    mcp_command = os.environ.get("CATCLAW_MCP_COMMAND", "")
    if not mcp_command:
        return [], None

    args_str = os.environ.get("CATCLAW_MCP_ARGS", "")
    args = [a.strip() for a in args_str.split(",") if a.strip()] if args_str else []

    try:
        from tools.mcp import MCPBridge, load_mcp_tools

        bridge = MCPBridge()
        print(f"🔌 正在连接 MCP Server: {mcp_command} {' '.join(args)}")
        bridge.connect(mcp_command, args)
        mcp_tools = load_mcp_tools(bridge)
        print(f"   ✅ 已加载 {len(mcp_tools)} 个 MCP 工具: {[t.name for t in mcp_tools]}")
        return mcp_tools, bridge
    except Exception as e:
        print(f"   ⚠️  MCP 连接失败: {e}")
        return [], None


def run_chat() -> None:
    """运行对话循环。"""
    print("=" * 60)
    print("🐱 CatClaw — Agent with Goal + Memory + MCP")
    print("=" * 60)
    print("内置工具: read, write, edit, bash, grep, find, ls, search")
    print("记忆: 对话持久化 + 自动压缩 + 长期记忆")
    print("Goal 命令: /goal <goal>, /goal status, /goal clear")
    print("输入 'quit' 或 'exit' 退出\n")

    goal = GoalState()

    # ---- MCP 工具加载 ----
    mcp_tools, mcp_bridge = _load_mcp_tools()
    print()

    # ---- 初始化 Memory ----
    memory = Memory()
    if memory.messages:
        print(f"📝 已恢复 {len(memory.messages)} 条历史消息")

    # ---- 初始化 ToolExecutor ----
    executor = ToolExecutor()

    # goal_complete 工具
    goal_tool = make_goal_complete_tool(goal)
    executor.tools.append(goal_tool)
    executor.tool_map[goal_tool.name] = goal_tool

    # MCP 工具
    for mt in mcp_tools:
        executor.tools.append(mt)
        executor.tool_map[mt.name] = mt

    # ---- shared 全局状态 ----
    shared.clear()
    shared["memory"] = memory
    shared["goal"] = goal
    shared["tools"] = [t.to_llm_format() for t in get_tools()]
    shared["tools"].append(goal_tool.to_llm_format())
    for mt in mcp_tools:
        shared["tools"].append(mt.to_llm_format())
    shared["tool_executor"] = executor
    shared["mcp_bridge"] = mcp_bridge

    # ---- 构建工作流 ----
    chat = ChatNode()
    tool_call = ToolCallNode()

    chat - "tool_call" >> tool_call
    tool_call - "chat" >> chat
    flow = Flow(chat)

    # ---- 主循环 ----
    while True:
        try:
            user_input = input("👤 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.startswith("/goal"):
            command = user_input.removeprefix("/goal").strip()

            if not command or command == "status":
                if goal.text:
                    print(f"\n🎯 Goal: {goal.text}\nActive: {goal.active}\n")
                else:
                    print("\n🎯 No active goal. Use /goal <goal> to start one.\n")
                continue

            if command == "clear":
                goal.text = None
                goal.active = False
                print("\n🎯 Goal cleared.\n")
                continue

            goal.text = command
            goal.active = True
            print(f"\n🎯 Goal started: {goal.text}\n")
            run_goal(flow, goal)
            continue

        memory.add_message({"role": "user", "content": user_input})
        flow.run(None)


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("OPENAI_BASE_URL"):
        print("⚠️  提示：请先设置环境变量 OPENAI_API_KEY 和 OPENAI_BASE_URL")
        return

    run_chat()


if __name__ == "__main__":
    main()
