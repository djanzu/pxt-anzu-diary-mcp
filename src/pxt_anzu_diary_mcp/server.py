import asyncio

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio
import dotenv
import os, sys
import requests
import logging
from pathlib import Path

# ログディレクトリを作成
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# ログファイルのパス
log_file = log_dir / "server.log"

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        #  logging.StreamHandler()  # コンソールにも出力
    ]
)
logger = logging.getLogger(__name__)

# 環境変数を読み込み
dotenv.load_dotenv()
DIARY_API_BASE = os.getenv("DIARY_API_BASE")

server = Server("pxt-anzu-diary-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="add-note",
            description="日記を追加します",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["date", "content"],
            },
        ),
        types.Tool(
            name = "get-note",
            description="指定された年の日記を取得します",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                },
                "required": ["year"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can modify server state and notify clients of changes.
    """
    if name != "add-note" and name != "get-note":
        raise ValueError(f"Unknown tool: {name}")

    if not arguments:
        raise ValueError("Missing arguments")

    params = {}
    if arguments.get("year"):
        # get用
        year = arguments.get("year")
        params["year"] = year
    if arguments.get("content"):
        # post用
        content = arguments.get("content")
        params["content"] = content
    if arguments.get("date"):
        # post用
        date = arguments.get("date")
        params["date"] = date

    # ツールごとに条件チェック
    if name == "add-note":
        if not content:
            raise ValueError("Missing content")
        # post処理
        response = requests.post(f"{DIARY_API_BASE}/diary", params=params)
        return [
            types.TextContent(
                type="text",
                text=f"Added content: {content}",
            )
        ]
    elif name == "get-note":
        if not year:
            raise ValueError("Missing year")
        # get処理
        response = requests.get(f"{DIARY_API_BASE}/diary?year={year}")
        entries = response.json()['items']
        text = "\n".join([f"date {x['date']} \n内容: {x['content']}" for x in entries])
        # logger.debug(text)
        return [
            types.TextContent(
                type="text",
                text=text,
            )
        ]

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="pxt-anzu-diary-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )