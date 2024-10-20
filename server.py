import asyncio
import logging
from aiohttp import web, WSMsgType
import zmq
import zmq.asyncio
import time
import os
from queue import Queue, Empty
import threading
from threading import Event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")


async def index(request):
    with open("index.html", "r") as f:
        content = f.read()
    return web.Response(content_type="text/html", text=content)

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    incoming_client_frames = request.app['incoming_client_frames']
    processed_frames = request.app['processed_frames']

    try:
        async for msg in ws:
            if msg.type == WSMsgType.BINARY:
                incoming_client_frames.put(msg.data)
                while not processed_frames.empty():
                    processed_frame = processed_frames.get()
                    await ws.send_bytes(processed_frame)
            elif msg.type == WSMsgType.ERROR:
                logger.error("WebSocket connection closed with exception %s", ws.exception())
    finally:
        pass

    return ws

async def on_shutdown(app):
    print("Starting shutdown")
    app['shutdown'].set()
    for ws in set(app['websockets']):
        await ws.close(code=WSMsgType.CLOSE, message="Server shutdown")
    app['websockets'].clear()
    app['distribute_thread'].join()
    app['collect_thread'].join()

def distribute_loop(app):
    incoming_client_frames = app['incoming_client_frames']
    
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    ipc_path = os.path.join(os.getcwd(), ".distribute_socket")
    socket.bind(f"ipc://{ipc_path}")
    socket.setsockopt(zmq.LINGER, 0)

    while not app['shutdown'].is_set():
        try:
            frame = incoming_client_frames.get(timeout=1)
            timestamp = time.time()
            socket.send_multipart([str(timestamp).encode(), frame])
        except Empty:
            continue
        
    socket.close()
    context.destroy()
        
def collect_loop(app):
    processed_frames = app['processed_frames']
    
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    ipc_path = os.path.join(os.getcwd(), ".collect_socket")
    socket.bind(f"ipc://{ipc_path}")
    socket.setsockopt(zmq.RCVTIMEO, 1000)
    socket.setsockopt(zmq.LINGER, 0)
    
    recent_timestamp = 0
    while not app['shutdown'].is_set():
        try:
            timestamp, frame = socket.recv_multipart()
            timestamp = float(timestamp)
            if timestamp > recent_timestamp:
                recent_timestamp = timestamp
                processed_frames.put(frame)
            else:
                print(f"dropping out-of-order frame: {1000*(recent_timestamp - timestamp):.1f}ms late")
        except zmq.Again:
            continue

    socket.close()
    context.destroy()

async def on_startup(app):
    app['incoming_client_frames'] = Queue()
    app['processed_frames'] = Queue()
    app['shutdown'] = Event()
    app['distribute_thread'] = threading.Thread(target=distribute_loop, args=(app,), daemon=True)
    app['collect_thread'] = threading.Thread(target=collect_loop, args=(app,), daemon=True)
    app['distribute_thread'].start()
    app['collect_thread'].start()

def main():
    app = web.Application()
    app['websockets'] = set()
    app.router.add_get("/", index)
    app.router.add_get("/ws", websocket_handler)
    app.on_shutdown.append(on_shutdown)
    app.on_startup.append(on_startup)

    web.run_app(app, access_log=None, port=8080)

if __name__ == "__main__":
    main()
