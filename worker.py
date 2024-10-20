import zmq
import cv2
import numpy as np
import os
import time
import random


def process_image(image_data, quality=50):
    # if random.random() < 0.1:
    #     time.sleep(0.5)
    
    # Decode the image
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Process the image (invert colors)
    processed_img = cv2.bitwise_not(img)
    
    # Encode the processed image
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    _, buffer = cv2.imencode(".jpg", processed_img, encode_param)
    return buffer.tobytes()


def main():

    print("Worker started")

    context = zmq.Context()
    
    pull_socket = context.socket(zmq.PULL)
    ipc_path = os.path.join(os.getcwd(), ".distribute_socket")
    pull_socket.connect(f"ipc://{ipc_path}")
    pull_socket.setsockopt(zmq.RCVTIMEO, 1000)
    pull_socket.setsockopt(zmq.LINGER, 0)

    push_socket = context.socket(zmq.PUSH)
    ipc_path = os.path.join(os.getcwd(), ".collect_socket")
    push_socket.connect(f"ipc://{ipc_path}")
    push_socket.setsockopt(zmq.SNDTIMEO, 1000)
    push_socket.setsockopt(zmq.LINGER, 0)
    
    maximum_delay = 1

    try:
        while True:
            try:
                timestamp, frame_data = pull_socket.recv_multipart()
                delay = time.time() - float(timestamp)
                if delay > maximum_delay:
                    print(f"dropping frame: {1000*delay:.1f}ms late")
                    continue
                processed_frame = process_image(frame_data)
                push_socket.send_multipart([timestamp, processed_frame])
            except zmq.Again:
                continue
    except KeyboardInterrupt:
        pass
    print("Worker stopped")


if __name__ == "__main__":
    main()
