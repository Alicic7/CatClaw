# 🐱 CatClaw

**从零开始构建的轻量级 AI Agent 框架**

CatClaw 是一个目标驱动的自主 AI Agent，配备 **8 个内置工具**、**对话记忆管理**（持久化 + 自动压缩 + 长期记忆）、**MCP 协议扩展**（可连接外部工具服务器）和 **Goal 目标循环**。

## 快速开始

```bash
# 1. 安装依赖
uv sync

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY 和 OPENAI_BASE_URL

# 3. 运行
uv run python main.py
```

## 环境变量

| 变量 | 说明 | 默认值 |
|:----:|:----:|:------:|
| `OPENAI_API_KEY` | API 密钥（**必填**） | - |
| `OPENAI_BASE_URL` | API 地址（**必填**） | `https://api.deepseek.com` |
| `OPENAI_MODEL_ID` | 模型 ID | `deepseek-v4-pro` |
| `CATCLAW_MCP_COMMAND` | MCP Server 启动命令（可选） | - |
| `CATCLAW_MCP_ARGS` | MCP Server 参数，逗号分隔（可选） | - |

## 功能特性

### 🛠 8 个内置工具

| 工具 | 功能 | 典型用法 |
|------|------|---------|
| `read` | 读取文件内容 | `read("main.py", offset=1, limit=50)` |
| `write` | 写入文件（自动创建父目录） | `write("out.txt", "hello")` |
| `edit` | 精确文本替换（单次匹配） | `edit("f.py", "old", "new")` |
| `bash` | 执行 Shell 命令 | `bash("ls -la")` |
| `grep` | 正则搜索文件内容 | `grep("class Node", ".", glob="*.py")` |
| `find` | Glob 模式查找文件 | `find("**/*.py")` |
| `ls` | 列出目录内容 | `ls(".")` |
| `search` | DuckDuckGo 网页搜索 | `search("Python Agent")` |

### 🧠 对话记忆管理

| 能力 | 说明 |
|------|------|
| **对话持久化** | 所有消息以 JSONL 格式实时追加写入 `chat_memory/session.jsonl`，重启后自动恢复 |
| **自动压缩** | 当 token 用量超过 128K × 90% 阈值时，LLM 自动将早期消息压缩为摘要，保留最后 4 条原始消息 |
| **长期记忆** | LLM 从对话中提取关键事实（用户偏好、重要事件等），写入 `chat_memory/MEMORY.md`，后续对话中自动注入 |
| **崩溃恢复** | 检测未完成的 `tool_calls` 序列，自动回滚到稳定状态 |

**相关文件**：
```
chat_memory/
├── session.jsonl    # 完整对话历史（JSONL 追加写入）
└── MEMORY.md        # 长期记忆（LLM 自动维护）
```

### 🔌 MCP 协议扩展

通过连接外部 MCP (Model Context Protocol) Server，可以动态加载更多工具。

#### 方式一：使用自带的示例 MCP Server

```bash
# .env 中添加：
CATCLAW_MCP_COMMAND="python"
CATCLAW_MCP_ARGS="tools/mcp/server.py"

uv run python main.py
```

启动时会自动连接并加载 `mcp_search`、`mcp_add`、`mcp_multiply` 三个工具。

#### 方式二：独立运行 MCP Server

```bash
# 启动内置 MCP Server（stdio 传输）
uv run python tools/mcp/server.py
```

Server 提供 `search`（网页搜索）、`add`（加法）、`multiply`（乘法）三个工具。

#### 方式三：连接第三方 MCP Server

```bash
# 例如连接 filesystem server
export CATCLAW_MCP_COMMAND="npx"
export CATCLAW_MCP_ARGS="-y,@modelcontextprotocol/server-filesystem,/path/to/allowed/dir"
uv run python main.py
```

**MCP 工具命名规则**：所有 MCP 工具会自动添加 `mcp_` 前缀，避免与内置工具冲突。例如 MCP Server 的 `search` 工具会注册为 `mcp_search`。

**架构**：`MCPBridge` 类在后台线程中维护与 MCP Server 的长连接（基于 FastMCP 3.x 的 `StdioTransport`），对外暴露同步 API，与现有的同步 Agent 循环无缝集成。

### 🎯 Goal 目标驱动

通过 `/goal` 命令启动自主执行模式，Agent 会持续运行直到完成目标：

| 命令 | 说明 |
|------|------|
| `/goal <描述>` | 启动一个目标，Agent 自主执行直到调用 `goal_complete` |
| `/goal status` | 查看当前目标状态 |
| `/goal clear` | 清除当前目标 |

**工作原理**：`run_goal()` 在每轮对话前注入目标提醒消息，引导 Agent 持续推进，直到 Agent 主动调用 `goal_complete` 工具标记完成。

## 交互示例

```
🐱 CatClaw — Agent with Goal + Memory + MCP
📝 已恢复 4 条历史消息

👤 You: 帮我搜索最新的 Python 3.14 发布时间
  [Tool] 执行: search({'query': 'Python 3.14 release date 2025'})
  [Tool] 结果: [{'title': 'Python 3.14.0 release...', ...

🐱 CatClaw: Python 3.14 预计在 2025 年 10 月发布...

👤 You: /goal 创建一个 hello.py 文件，输出 "Hello from CatClaw"

🎯 Goal started: 创建一个 hello.py 文件，输出 "Hello from CatClaw"

  [Tool] 执行: write({'path': 'hello.py', 'content': 'print("Hello from CatClaw")'})
  [Tool] 结果: Successfully wrote 30 bytes to hello.py
  [Tool] 执行: bash({'command': 'python hello.py'})
  [Tool] 结果: Hello from CatClaw
  [Tool] 执行: goal_complete({})
  [Tool] 结果: Goal complete

🐱 CatClaw: 目标完成！已创建 hello.py，运行验证通过。
```

## 项目结构

```
CatClaw/
├── core/
│   ├── node.py          # 工作流引擎 — Node + Flow（~56 行）
│   ├── llm.py           # LLM 调用接口（OpenAI 兼容协议）
│   └── memory.py        # 对话记忆管理（持久化 + 压缩 + 长期记忆）
├── tools/
│   ├── executor.py      # 工具解析与执行引擎
│   ├── builtins/        # 8 个内置工具
│   │   ├── read.py      #   文件读取（offset/limit + 截断）
│   │   ├── write.py     #   文件写入（自动创建父目录）
│   │   ├── edit.py      #   精确文本替换（唯一匹配）
│   │   ├── bash.py      #   Shell 命令执行（30KB/2000行截断）
│   │   ├── grep.py      #   内容搜索（ripgrep + Python 回退）
│   │   ├── find.py      #   文件查找（fd + Python glob 回退）
│   │   ├── ls.py        #   目录列表（500条限制）
│   │   ├── search.py    #   网页搜索（DuckDuckGo）
│   │   └── tool_def.py  #   Tool 数据类 + LLM 格式转换
│   └── mcp/             # MCP 协议扩展
│       ├── client.py    #   MCP 客户端（后台线程长连接 + 同步桥）
│       └── server.py    #   MCP 示例服务器（search/add/multiply）
├── main.py              # 主程序入口 — ChatNode + ToolCallNode + Goal
├── pyproject.toml
└── README.md
```

## 架构设计

CatClaw 的核心是一个 **~56 行的工作流引擎**，在此基础上逐层叠加能力：

```
                    ┌─────────────────────────┐
                    │      Goal Loop           │
                    │  run_goal() 外层循环       │
                    │  持续注入目标提醒           │
                    └───────────┬─────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                 Agent Loop                     │
        │         ChatNode ←→ ToolCallNode               │
        │    (LLM 决策)      (工具执行 + 结果回传)         │
        └───────┬───────────┬───────────┬───────────────┘
                │           │           │
    ┌───────────┴──┐  ┌─────┴─────┐  ┌─┴──────────────┐
    │   Memory     │  │ 8 Builtins│  │   MCP Bridge    │
    │ 持久化+压缩   │  │ 本地工具   │  │  外部工具扩展    │
    │ +长期记忆    │  │           │  │  (后台线程)      │
    └──────────────┘  └───────────┘  └─────────────────┘
```

核心设计模式：

- **`shared` 全局状态** — 模块级 `dict` 作为 DI 容器，`memory`、`tools`、`executor`、`goal` 都在其中，节点间直接读写
- **`Node` 基类** — `exec(payload) -> (action, next_payload)`，通过 `>>` 运算符串联
- **`Flow` 编排器** — 按 action 名称驱动节点跳转，直到无后继为止
- **`- "action"` 连线模式** — `chat - "tool_call" >> tool_call` 表示当 ChatNode 返回 `"tool_call"` 时跳转到 ToolCallNode
- **Agent 循环** — `ChatNode ↔ ToolCallNode` 构成工具调用的无限循环，直到 LLM 不再返回 `tool_calls`
- **Goal 循环** — `run_goal()` 外层持续注入 `/goal` 消息，直到 Agent 主动调用 `goal_complete` 工具
- **MCP 桥** — `MCPBridge` 后台线程维护长连接，通过 `asyncio.run_coroutine_threadsafe` 实现同步调用

## 依赖

| 包 | 用途 |
|----|------|
| `openai` | LLM API 客户端（兼容任何 OpenAI 协议服务） |
| `ddgs` | DuckDuckGo 网页搜索 |
| `fastmcp` | MCP 服务器框架 + 客户端（FastMCP 3.x） |
| `python-dotenv` | `.env` 环境变量加载 |
