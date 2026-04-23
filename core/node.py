import time
from typing import Any, Dict, Optional, Tuple

class Node:
    __slots__=("successors","action","max_retries","wait")
    successors: Dict[str, "Node"]
    action: str
    max_retries: int
    wait: float

    def __init__(self,max_retries:int=1,wait:float=0.0):
        self.successors={}
        self.action="default"
        self.max_retries=max_retries
        self.wait=wait

    def exec(self,payload)-> Tuple[str, Any]:
        raise NotImplementedError

    def _exec(self,payload)->Tuple[str,Any]:
        for cur_retry in range(self.max_retries):
            try:
                return self.exec(payload)
            except Exception as e:
                if cur_retry==self.max_retries-1:
                    raise e
                if self.wait>0:
                    time.sleep(self.wait)
        raise RuntimeError("Unreachable code")

    def __rshift__(self, other:"Node")->"Node":
        self.successors[self.action]=other
        self.action="default"
        return other

    def __sub__(self, action:str)->"Node":
        if not isinstance(action,str):
            raise TypeError("Action must be a string")
        self.action=action or "default"
        return self

class Flow:
    __slots__= "start_node"
    start_node:Node

    def __init__(self,start_node:Optional[Node]=None):
        self.start_node=start_node

    def run(self,payload)->Tuple[Optional[str],Any]:
        next_action,cur_node="default",self.start_node
        while cur_node:
            next_action,payload=cur_node._exec(payload)
            cur_node=cur_node.successors.get(next_action)
        return next_action,payload