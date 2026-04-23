from pathlib import Path
from ..register import register_tool

def return_write_tool_format():
    return dict(
        name="write",
        description="Write content to a file.Create parent directories if they do not exist.",
        parameters=dict(
            type="object",
            properties=dict(
                path=dict(type="string",description="File path to write to.",),
                content=dict(type="string",description="Content to write to the file.",),
                cwd=dict(
                    type="string",
                    description="Current working directory for resolving relative paths.",
                )
            ),
            required=["path","content"],
        ),
        fn=write_file,
    )

def write_file(path:str,content:str,cwd:str|None=None)->str:
    file_path=Path(cwd)/path if cwd else Path(path)
    file_path=file_path.resolve()
    file_path.parent.mkdir(parents=True,exist_ok=True)
    file_path.write_text(content,encoding="utf-8")
    return f"Successfully wrote {len(content)} bytes to {path}"

register_tool("write",write_file)