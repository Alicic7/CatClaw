import os
from os import truncate
from pathlib import Path
from tools.register import register_tool

PC_TYPE=os.getenv("PC_TYPE","unknown").lower()
DEFAULT_MAX_BYTES=30*1024

def return_read_tool_format():
    return dict(
        name="read",
        description="Read content from a file.Support offset and limit for large files.",
        parameters=dict(
            type="object",
            properties=dict(
                path=dict(type="string",description="File path to read.",),
                offset=dict(
                    type="integer",
                    description="Line number to start reading from (1-based).",
                ),
                limit=dict(type="integer",description="Maximum number of lines to read."),
                cwd=dict(
                    type="string",
                    description="Current working directory for resolving relative paths.",
                ),
            ),
            required=["path"],
        ),
        fn=read_file,
    )

def read_file(path:str,offset:int|None=None,limit:int|None=None,cwd:str|None=None):
    file_path=Path(cwd)/path if cwd else Path(path)
    file_path.resolve()

    if not file_path.exists():
        raise FileNotFoundError(f"File not found:{file_path}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a file:{file_path}")

    content=file_path.read_text(encoding="utf-8")
    lines=content.splitlines()

    total_line=len(lines)
    start_line=max(0,(offset or 1)-1)

    if start_line>=total_line:
        raise ValueError(f"Offset {offset} is out of range.Total lines:{total_line}")

    end_line=min(start_line+limit,total_line) if limit else total_line

    result='\n'.join(lines[start_line:end_line])

    result_bytes=result.encode("utf-8")
    if len(result_bytes)>DEFAULT_MAX_BYTES:
        truncated=result_bytes[:DEFAULT_MAX_BYTES].decode("utf-8",errors="ignore")
        last_line_id=truncated.rfind('\n')
        if last_line_id>0:
            truncated=truncated[:last_line_id]
        result=truncated
        end_line=start_line+truncated.count('\n')+1
        result += f"\n\n[showing lines {start_line + 1}-{end_line} of {total_line}({DEFAULT_MAX_BYTES // 1024}KB limit). Use offset={end_line + 1} to continue.]"

    elif limit and end_line < total_line:
        result += f"\n\n[{total_line - end_line} more lines in file. Use offset={end_line + 1} to continue.]"

    return result

register_tool("read",read_file)