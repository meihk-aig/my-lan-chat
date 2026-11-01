import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout


async def network_listener():
    """Gia lap nhan tin nhan tu Minh."""

    while True:
        await asyncio.sleep(1)

        print("[Minh] ok, which part?")

    # Co the thay bang code nhan du lieu tu server
    # qua socket hoac WebSocket.


async def chat():
    """Ham dieu khien chuong trinh chat."""

    session = PromptSession()

    print("[Quan] it's not enough content")

    # Tao tac vu nhan tin nhan chay nen
    listener_task = asyncio.create_task(network_listener())

    try:
        while True:

            # Cho phep nhan output ma khong pha dong nhap
            with patch_stdout():

                message = await session.prompt_async("> ")

            # Xu ly tin nhan nguoi dung
            if message.strip():

                print(f"[You] {message}")

    except (KeyboardInterrupt, EOFError):
        print("\nDa thoat khoi chat.")

    finally:
        # Huy task neu chua hoan thanh
        if not listener_task.done():
            listener_task.cancel()

            try:
                await listener_task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    asyncio.run(chat())
