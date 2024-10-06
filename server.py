import asyncio
import json
import logging
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCConfiguration, RTCIceServer
from aiortc.contrib.media import MediaRelay
import threading
import queue
import ssl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pc")

pcs = set()
relay = MediaRelay()

def invert_worker(input_queue, output_queue):
    while True:
        img = input_queue.get()
        if img is None:
            break
        
        # Invert the image using NumPy
        inverted_img = 255 - img
        
        try:
            output_queue.put(inverted_img, block=False)
        except queue.Full:
            output_queue.get()
            output_queue.put(inverted_img, block=False)

class VideoTransformTrack(VideoStreamTrack):
    def __init__(self, track):
        super().__init__()
        self.track = track
        self.frame_num = 0
        self.input_queue = queue.Queue(maxsize=1)
        self.output_queue = queue.Queue(maxsize=1)
        self.filter_thread = threading.Thread(target=invert_worker, args=(self.input_queue, self.output_queue))
        self.filter_thread.start()
        self.latest_frame = None

    async def recv(self):
        frame = await self.track.recv()

        img = frame.to_ndarray(format="rgb24")
        
        try:
            self.input_queue.put(img, block=False)
        except queue.Full:
            pass

        try:
            inverted_img = self.output_queue.get(block=False)
            new_frame = frame.from_ndarray(inverted_img, format="rgb24")
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base
            self.latest_frame = new_frame
        except queue.Empty:
            pass
        
        if self.frame_num % 120 == 0:
            print(f"Frame {self.frame_num} resolution: {frame.width}x{frame.height}")
            try:
                print(f"Frame {self.frame_num} output resolution: {self.latest_frame.width}x{self.latest_frame.height}")
            except AttributeError:
                print(f"Frame {self.frame_num} output resolution: None")

        self.frame_num += 1
        return self.latest_frame or frame

    def stop(self):
        self.input_queue.put(None)
        self.filter_thread.join()

async def index(request):
    content = open('index.html', 'r').read()
    return web.Response(content_type='text/html', text=content)

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params['sdp'], type=params['type'])

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on('iceconnectionstatechange')
    async def on_iceconnectionstatechange():
        logger.info('ICE connection state is %s', pc.iceConnectionState)
        logger.info('Local candidates: %s', pc.localDescription.sdp)
        logger.info('Remote candidates: %s', pc.remoteDescription.sdp)
        if pc.iceConnectionState == 'failed':
            await pc.close()
            pcs.discard(pc)

    @pc.on('icegatheringstatechange')
    def on_icegatheringstatechange():
        logger.info('ICE gathering state is %s', pc.iceGatheringState)

    @pc.on('signalingstatechange')
    def on_signalingstatechange():
        logger.info('Signaling state is %s', pc.signalingState)

    @pc.on('track')
    def on_track(track):
        logger.info('Track %s received', track.kind)

        if track.kind == 'video':
            local_video = VideoTransformTrack(relay.subscribe(track))
            pc.addTrack(local_video)

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    response = {'sdp': pc.localDescription.sdp, 'type': pc.localDescription.type}
    return web.Response(content_type='application/json', text=json.dumps(response))

async def on_shutdown(app):
    print("Shutting down...")
    
    coros = []
    for pc in pcs:
        coros.append(pc.close())
        for sender in pc.getSenders():
            if isinstance(sender.track, VideoTransformTrack):
                sender.track.stop()
    await asyncio.gather(*coros)
    pcs.clear()

    print("Application shut down successfully.")

if __name__ == '__main__':
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_post('/offer', offer)
    app.on_shutdown.append(on_shutdown)
    
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain('cert.pem', 'key.pem')
    
    web.run_app(app, access_log=None, port=8443, ssl_context=ssl_context)