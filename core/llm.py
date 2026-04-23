import os
from typing import Any, Dict, List

from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionMessage

KEY=os.getenv("OPENAI_API_KEY")
URL=os.getenv("OPENAI_BASE_URL")
MODEL=os.getenv("OPENAI_MODEL","gpt-3.5-turbo")

def call_llm(
    prompt:str|None=None,
    messages:List[Dict[str,Any]]|None=None,
    tools:List[Dict[str,Any]]|None=None,
    system_prompt:str|None=None,
)->Dict[str,Any]:
    client = OpenAI(
        api_key=KEY,
        base_url=URL,
    )
    msgs=[]
    if system_prompt:
        msgs.extend([{"role": "system","content":system_prompt}])
    if messages:
        msgs.extend(messages)
    elif prompt:
        msgs.extend([{"role":"user","content":prompt}])
    else:
        raise ValueError("Either prompt or messages must be provided")

    kwargs:Dict[str,Any]={
        "model":MODEL,
        "messages":msgs,
    }

    if tools:
        kwargs["tools"]=tools
        kwargs["tool_choice"]="auto"

    response:ChatCompletion|Stream[ChatCompletionChunk]=(
        client.chat.completions.create(**kwargs)
    )

    message:ChatCompletionMessage=response.choices[0].message

    result:Dict[str,Any]={"role":"assistant","content":message.content or""}

    reasoning_content=getattr(message,"reasoning_content",None)
    if reasoning_content:
        result["reasoning_content"]=reasoning_content
    # "tool_calls"是大模型返回的工具调用指令，大模型没办法直接操控电脑
    if message.tool_calls:
        result["tool_calls"]=[tool_call.model_dump() for tool_call in message.tool_calls]

    return result

if __name__ == "__main__":
    prompt="求生之路2的英文是什么？"
    response=call_llm(prompt=prompt)
    print(response)
