import time
from ddgs import DDGS
from ..register import register_tool

def return_search_tool_format():
    return dict(
        name="search",
        description=("Search the latest information from the web."
                     "Use this tool when the question involves recent events, model versions, product release dates, or fact-checking."),
        parameters=dict(
            type="object",
            properties=dict(
                query=dict(type="string",description="The search query.",),
                max_retries=dict(type="integer",description="Maximum number of retries for the search query in case of failures."),
            ),
            required=["query"],
        ),
        fn=search,
    )


def search(query: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            with DDGS() as ddg:
                raw_results = ddg.text(query, max_results=5)
                results = list(raw_results)
                if not results:
                    return f"No results found for query: '{query}'"
                simplified = [
                    f"Title: {r.get('title', 'N/A')}\nSnippet: {r.get('body', 'N/A')}"
                    for r in results
                ]
                return "\n---\n".join(simplified)
        except Exception as e:
            if attempt<max_retries-1:
                time.sleep(1)
                continue
            else:
                return f"Search failed after {max_retries} retries. Error: {str(e)}"
    return None

register_tool("search",search)