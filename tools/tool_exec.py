import json
from typing import List
from openai.types.chat import ChatCompletionMessageFunctionToolCall
from tools.register import get_tool

def stringify_result(value):
    if isinstance(value,dict):
        return json.dumps(value,ensure_ascii=False)
    return str(value)

def parse_openai_tool_calls(tool_calls:List[ChatCompletionMessageFunctionToolCall]):
    tool_call_results=[]
    for tool_call in tool_calls:
        tool_call_id = tool_call["id"]
        tool_name = tool_call["function"]["name"]
        tool_args = tool_call["function"]["arguments"]
        func=get_tool(tool_name)
        try:
            tool_args=json.loads(tool_args)
        except json.JSONDecodeError:
            tool_call_results.append(
                dict(
                    role="tool",
                    tool_call_id=tool_call_id,
                    content=f"Error parsing arguments for tool {tool_name}: Invalid JSON",
                )
            )
        if not func:
            tool_call_results.append(
                dict(
                    role="tool",
                    tool_call_id=tool_call_id,
                    content=f"Tool {tool_name} not found",
                )
            )
        else:
            try:
                result=func(**tool_args)
                tool_call_results.append(
                    dict(
                        role="tool",
                        tool_call_id=tool_call_id,
                        content=stringify_result(result),
                    )
                )
            except Exception as e:
                tool_call_results.append(
                    dict(
                        role="tool",
                        tool_call_id=tool_call_id,
                        content=f"Error executing tool {tool_name}:{str(e)}",
                    )
                )
    return tool_call_results