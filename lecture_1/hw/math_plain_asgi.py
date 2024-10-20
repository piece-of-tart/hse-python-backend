from typing import Any, Awaitable, Callable
import urllib.parse
import math
import uvicorn
import asyncio
import json
import re


async def send_not_found(send):
    await send(
        {
            "type": "http.response.start",
            "status": 404,
            "headers": [
                [b"content-type", b"text/plain"],
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": b"404 Not Found",
        }
    )


async def send_unprocessable_ent(send):
    await send(
        {
            "type": "http.response.start",
            "status": 422,
            "headers": [[b"content-type", b"text/plain"]],
        }
    )
    await send({"type": "http.response.body", "body": b"422 Unprocessable Entity"})


async def send_bad_request(send):
    await send(
        {
            "type": "http.response.start",
            "status": 400,
            "headers": [[b"content-type", b"text/plain"]],
        }
    )
    await send({"type": "http.response.body", "body": b"400 Bad Request"})


async def send_response(body: str, send):
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": body.encode(),
        }
    )


async def process_factorial(scope, send):
    query_string = scope.get("query_string", b"").decode("utf-8")
    query_params = urllib.parse.parse_qs(query_string)
    n_params = query_params.get("n")
    if n_params == None or len(n_params) == 0:
        await send_unprocessable_ent(send)
        return
    n_param = n_params[0]
    print("query: {n_param}")
    try:
        n = int(n_param)
        if n < 0:
            await send_bad_request(send)
            return
        result = math.factorial(n)
        await send_response(str(json.dumps({"result": result})), send)
    except ValueError:
        await send_unprocessable_ent(send)


async def process_fibonacci(n_param, send):
    try:
        n = int(n_param)
        if n < 0:
            await send_bad_request(send)
            return
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        await send_response(str(json.dumps({"result": b})), send)
    except ValueError:
        await send_unprocessable_ent(send)


async def process_mean(scope, receive, send):
    body = b""
    more_body = True

    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)

    arr = json.loads(body.decode())
    if arr == None:
        await send_unprocessable_ent(send)
        return
    elif len(arr) == 0:
        await send_bad_request(send)
        return
    if not all([isinstance(x, (int, float)) for x in arr]):
        await send_unprocessable_ent(send)
        return
    result = sum(arr) / len(arr)
    await send_response(str(json.dumps({"result": result})), send)


async def app(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    print(f"get: {scope.get('path')}")
    if scope.get("method") != "GET":
        await send_not_found(send)
        return
    if scope.get("path") == "/factorial":
        await process_factorial(scope, send)
    else:
        m = re.search(r"/fibonacci/(.*)", scope.get("path"))
        if m:
            await process_fibonacci(m.group(1), send)
        elif scope.get("path") == "/mean":
            await process_mean(scope, receive, send)
        else:
            await send_not_found(send)


async def main():
    config = uvicorn.Config("math_plain_asgi:app", port=23542, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
