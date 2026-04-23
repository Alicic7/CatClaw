from dotenv import load_dotenv
# 加载.env文件
load_dotenv()

from core import Node,Flow,call_llm
from tools import get_tools, parse_openai_tool_calls

SYSTEM_PROMPT=(
    "你是一个会调用工具的助手。"
    "当问题涉及最新信息、模型版本、产品发布时间或事实核验时，优先调用 search 工具，再基于搜索结果回答。"
    "若问题是本地文件/代码相关，优先使用 read/grep/find/ls 等本地工具。"
)
shared=dict()

class ChatNode(Node):
    def exec(self,payload):
        messages=shared.get("messages",[])
        tools=shared.get("tools",[])
        rt_message=call_llm(
            messages=messages,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
        )
        messages.append(rt_message)
        shared["messages"]=messages
        if rt_message.get("tool_calls"):
            return "tool_call",rt_message
        return "output",rt_message

class ToolCallNode(Node):
    def exec(self,payload):
        messages=shared.get("messages",[])
        tool_calls=payload.get("tool_calls",[])
        tool_call_results=parse_openai_tool_calls(tool_calls)
        messages.extend(tool_call_results)
        shared["messages"]=messages
        return "chat",None

class OutputNode(Node):
    def exec(self,payload):
        content=payload.get("content","")
        print(f"\n🤖 Assistant:{content}\n")
        return "default",None

def run_chat():
    shared.clear()
    shared["messages"]=[]
    shared["tools"]=[tool.to_llm_format() for tool in get_tools()]

    chat_node=ChatNode()
    toolcall_node=ToolCallNode()
    output_node=OutputNode()

    chat_node-"tool_call">>toolcall_node
    toolcall_node-"chat">>chat_node
    chat_node-"output">>output_node

    while True:
        user_input=input("👤 You:").strip()

        if user_input.lower() in {"exit","quit"}:
            print("Exit chat.")
            break

        if not user_input:
            continue

        shared["messages"].append({"role":"user","content":user_input})
        flow=Flow(chat_node)
        flow.run(None)

if __name__ == "__main__":
    run_chat()