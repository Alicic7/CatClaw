from pathlib import Path
from ..register import register_tool

DEFAULT_LIMIT=500
DEFAULT_MAX_BYTES=30*1024

def return_ls_tool_format():
    return dict(
        name="ls",
        description="List directory contents.Returns entries with '/' suffix for directories.",
        parameters=dict(
            type="object",
            properties=dict(
                path=dict(type="string",description="Directory path to list.",),
                limit=dict(
                    type="integer",
                    description="Maximum number of entries to list.Default is 500.",
                ),
                cwd=dict(
                    type="string",
                    description="Current working directory for resolving relative paths.",
                ),
            ),
        required=[],
        ),
        fn=ls,
    )

def ls(path:str|None=None,limit:int|None=None,cwd:str|None=None)->str:
    dir_path=Path(cwd)/(path or '.') if cwd else Path(path or '.')
    dir_path=dir_path.resolve()

    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found:{dir_path}")

    if not dir_path.is_dir():
        raise ValueError(f"Path is not a directory:{dir_path}")

    limit=limit or DEFAULT_LIMIT

    try:
        entries=list(dir_path.iterdir())
    except PermissionError:
        raise PermissionError(f"Permission denied: {dir_path}")

    entries.sort(key=lambda e:e.name.lower())
    results=[]

    for entry in entries:
        if len(results)>=limit:
            break
        suffix='/' if entry.is_dir() else ''
        results.append(entry.name+suffix)

    if not results:
        return "Directory is empty."

    output='\n'.join(results)
    if len(output.encode("utf-8"))>DEFAULT_MAX_BYTES:
        output = output.encode("utf-8")[:DEFAULT_MAX_BYTES].decode(
            "utf-8", errors="ignore"
        )
        output += f"\n\n[{DEFAULT_MAX_BYTES // 1024}KB limit reached, output truncated]"

    if len(entries) >= limit:
        output += f"\n\n[{limit} entries limit reached. Use limit={limit * 2} for more]"

    return output

register_tool("ls",ls)