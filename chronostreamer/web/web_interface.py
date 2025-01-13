import json
import asyncio
import websockets

# Assuming save_config is added for saving changes
from chronostreamer.utils import load_config, save_config

# Global config variable for caching config in memory
current_config = load_config()


async def config_sync(websocket, path):
    # Send initial configuration to new client
    await websocket.send(json.dumps(current_config))

    async for message in websocket:
        # Update received from the client
        new_config = json.loads(message)
        # Update global config and save it
        current_config.update(new_config)
        save_config(current_config)
        # Broadcast updated config to all connected clients
        await broadcast_config(new_config)


async def broadcast_config(updated_config):
    for ws in connected_clients:
        await ws.send(json.dumps(updated_config))


connected_clients = set()


async def server(websocket, path):
    connected_clients.add(websocket)
    try:
        await config_sync(websocket, path)
    finally:
        connected_clients.remove(websocket)


# Start the server
start_server = websockets.serve(server, "localhost", 6789)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
