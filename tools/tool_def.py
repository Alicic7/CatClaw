from typing import Callable, Dict, List

class Tool:
    __slots__="name","description","parameters","fn"
    name:str
    description:str
    parameters:Dict
    fn:Callable

    def __init__(self,name:str,description:str,parameters:Dict,fn:Callable):
        self.name=name
        self.description=description
        self.parameters=parameters
        self.fn=fn

    def to_llm_format(self)->Dict:
        return {
            "type":"function",
            "function":{
                "name":self.name,
                "description":self.description,
                "parameters":self.parameters,
            },
        }

    def execute(self,**kwargs):
        return self.fn(**kwargs)

def get_tools()->List[Tool]:
    from .builtins import(
        return_ls_tool_format,
        return_read_tool_format,
        return_search_tool_format,
        return_write_tool_format,
    )
    return [
        Tool(**return_ls_tool_format()),
        Tool(**return_read_tool_format()),
        Tool(**return_search_tool_format()),
        Tool(**return_write_tool_format()),
    ]