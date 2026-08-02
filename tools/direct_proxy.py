import asyncio
from contextlib import suppress


LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8899
BUFFER_SIZE = 65536

# 当前只允许转发项目正在使用的两个模型接口。
ALLOWED_HOSTS = {
    "api.deepseek.com",
    "dashscope.aliyuncs.com",
}


async def copy_stream(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    """
    持续转发一侧收到的数据。
    """

    try:
        while True:
            data = await reader.read(BUFFER_SIZE)

            if not data:
                break

            writer.write(data)
            await writer.drain()

    except (
        ConnectionError,
        asyncio.CancelledError,
    ):
        pass


async def close_writer(
    writer: asyncio.StreamWriter,
) -> None:
    """
    安全关闭网络连接。
    """

    with suppress(Exception):
        writer.close()
        await writer.wait_closed()


async def handle_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
) -> None:
    """
    接收Docker中的HTTP CONNECT请求，
    再由Windows直接连接模型供应商。
    """

    peer = client_writer.get_extra_info("peername")
    remote_writer: asyncio.StreamWriter | None = None

    try:
        header_data = await asyncio.wait_for(
            client_reader.readuntil(b"\r\n\r\n"),
            timeout=15,
        )

        request_line = (
            header_data
            .split(b"\r\n", 1)[0]
            .decode("latin1")
        )

        parts = request_line.split(" ", 2)

        if len(parts) != 3:
            raise ValueError(
                "Invalid HTTP request line."
            )

        method, target, _ = parts

        if method.upper() != "CONNECT":
            client_writer.write(
                b"HTTP/1.1 405 Method Not Allowed\r\n"
                b"Connection: close\r\n"
                b"Content-Length: 0\r\n"
                b"\r\n"
            )
            await client_writer.drain()
            return

        host, separator, port_text = target.rpartition(":")

        if not separator:
            host = target
            port = 443
        else:
            port = int(port_text)

        host = host.strip().lower()

        if host not in ALLOWED_HOSTS:
            client_writer.write(
                b"HTTP/1.1 403 Forbidden\r\n"
                b"Connection: close\r\n"
                b"Content-Length: 0\r\n"
                b"\r\n"
            )
            await client_writer.drain()

            print(
                f"[BLOCKED] {peer} -> {host}:{port}",
                flush=True,
            )
            return

        if port != 443:
            raise ValueError(
                "Only HTTPS port 443 is allowed."
            )

        remote_reader, remote_writer = (
            await asyncio.wait_for(
                asyncio.open_connection(
                    host=host,
                    port=port,
                ),
                timeout=20,
            )
        )

        client_writer.write(
            b"HTTP/1.1 200 Connection Established\r\n"
            b"Proxy-Agent: LLM-Direct-Proxy\r\n"
            b"\r\n"
        )
        await client_writer.drain()

        print(
            f"[CONNECTED] {peer} -> {host}:{port}",
            flush=True,
        )

        client_to_remote = asyncio.create_task(
            copy_stream(
                client_reader,
                remote_writer,
            )
        )

        remote_to_client = asyncio.create_task(
            copy_stream(
                remote_reader,
                client_writer,
            )
        )

        done, pending = await asyncio.wait(
            {
                client_to_remote,
                remote_to_client,
            },
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        await asyncio.gather(
            *done,
            *pending,
            return_exceptions=True,
        )

    except asyncio.IncompleteReadError:
        pass

    except Exception as exc:
        print(
            f"[FAILED] {peer}: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

        with suppress(Exception):
            client_writer.write(
                b"HTTP/1.1 502 Bad Gateway\r\n"
                b"Connection: close\r\n"
                b"Content-Length: 0\r\n"
                b"\r\n"
            )
            await client_writer.drain()

    finally:
        if remote_writer is not None:
            await close_writer(remote_writer)

        await close_writer(client_writer)


async def main() -> None:
    server = await asyncio.start_server(
        handle_client,
        host=LISTEN_HOST,
        port=LISTEN_PORT,
    )

    addresses = ", ".join(
        str(server_socket.getsockname())
        for server_socket in server.sockets or []
    )

    print(
        "LLM Direct Proxy is running.",
        flush=True,
    )
    print(
        f"Listening on: {addresses}",
        flush=True,
    )
    print(
        "Allowed hosts:",
        ", ".join(sorted(ALLOWED_HOSTS)),
        flush=True,
    )
    print(
        "Keep this window open.",
        flush=True,
    )

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(
            "\nLLM Direct Proxy stopped.",
            flush=True,
        )