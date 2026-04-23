# 环境设置

- 安装uv（如果系统还没装）

- 在项目根目录下新建文件".env"并写入以下内容：

  ``` bash
  OPENAI_API_KEY="你的API_KEY"
  OPENAI_BASE_URL="模型地址"
  OPENAI_MODEL="模型名称"
  ```

- 在终端运行`uv run main.py`

# 测试用例
- 在终端输入`请你阅读项目根目录下的文件"米塔.txt"并将里面的内容变为MarkDown文档写入到项目的根目录下面，文件命名为"MiSide.md"`