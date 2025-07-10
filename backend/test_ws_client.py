import asyncio
import websockets

async def test_connection():
    uri = "ws://192.168.1.142:8765/"
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Successfully connected to {uri}")
            await websocket.send("Hello from client!")
            response = await websocket.recv()
            print(f"Received: {response}")
    except Exception as e:
        print(f"Failed to connect or communicate: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
