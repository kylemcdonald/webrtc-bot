import asyncio
import logging
from aiohttp import web, WSMsgType
import cv2
import numpy as np
import ssl
import threading
import queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

class ImageProcessor:
    def __init__(self):
        self.input_queue = queue.Queue(maxsize=1)
        self.output_queue = queue.Queue(maxsize=1)
        self.thread = threading.Thread(target=self.process_images)
        self.thread.start()

    def process_images(self):
        while True:
            img = self.input_queue.get()
            if img is None:
                break
            
            # Invert the image
            inverted_img = img # cv2.bitwise_not(img)
            
            try:
                self.output_queue.put(inverted_img, block=False)
            except queue.Full:
                self.output_queue.get()
                self.output_queue.put(inverted_img, block=False)

    def process(self, img):
        try:
            self.input_queue.put(img, block=False)
        except queue.Full:
            self.input_queue.get()
            self.input_queue.put(img, block=False)

        try:
            return self.output_queue.get(block=False)
        except queue.Empty:
            return img

    def stop(self):
        self.input_queue.put(None)
        self.thread.join()

async def index(request):
    with open('index.html', 'r') as f:
        content = f.read()
    return web.Response(content_type='text/html', text=content)

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    processor = ImageProcessor()

    try:
        async for msg in ws:
            if msg.type == WSMsgType.BINARY:
                # Decode the image
                nparr = np.frombuffer(msg.data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                # Process the image
                processed_img = processor.process(img)

                # Encode the processed image to JPEG with reduced quality
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 10]
                _, buffer = cv2.imencode('.jpg', processed_img, encode_param)
                
                # Send the processed image back as binary data
                await ws.send_bytes(buffer.tobytes())
            elif msg.type == WSMsgType.ERROR:
                logger.error('WebSocket connection closed with exception %s', ws.exception())
    finally:
        processor.stop()

    return ws

async def on_shutdown(app):
    for ws in set(app['websockets']):
        await ws.close(code=WSMsgType.CLOSE, message='Server shutdown')
    app['websockets'].clear()

def main():
    app = web.Application()
    app['websockets'] = set()
    app.router.add_get('/', index)
    app.router.add_get('/ws', websocket_handler)
    app.on_shutdown.append(on_shutdown)
    
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain('cert.pem', 'key.pem')
    
    web.run_app(app, access_log=None, port=8443, ssl_context=ssl_context)

if __name__ == '__main__':
    main()
