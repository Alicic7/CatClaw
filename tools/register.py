global_dict=dict()

def register_tool(name,func):
    global_dict[name]=func
    return func

def get_tool(name):
    return global_dict.get(name)