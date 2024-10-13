# webrtc-bot

## Setup

0. Install Python (if not already installed):

   ```
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv
   ```

1. Clone the repository:
   ```
   git clone https://github.com/kylemcdonald/webrtc-bot.git
   cd webrtc-bot
   ```

2. Create a virtual environment:
   ```
   python3 -m venv venv
   ```

3. Activate the virtual environment:
   ```
   source venv/bin/activate
   ```

4. Install the required dependencies:
   ```
   pip install aiohttp opencv-python-headless numpy
   ```

5. Generate SSL certificates (required for HTTPS):
   ```
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/OU=Unit/CN=webrtc-bot"
   ```

6. Run the server:
   ```
   python server.py
   ```

7. Open a web browser and navigate to `https://localhost:8443`

Note: You will need to accept the self-signed certificate warning in your browser.

To deactivate the virtual environment when you're done, simply run:
```
deactivate
```

## Docker Setup

Alternatively, you can use Docker to run the application:

1. Make sure you have Docker installed on your system.

2. Build the Docker image:
   ```
   docker build -t webrtcbot .
   ```

3. Run the Docker container:
   ```
   docker run -it --rm --net host webrtcbot
   ```

Note that if you try to run the Docker container another way, it might not work due to the huge port range required by WebRTC. This is indicated in the Dockerfile as `EXPOSE 49152-65535/udp` but it's very common for some of these ports to be in use. I followed the tips in [this article](https://flashphoner.com/load-webrtc-with-containers-or-how-i-ran-wcs-in-docker/).

4. Open a web browser and navigate to `https://localhost:8443`

Note: You will still need to accept the self-signed certificate warning in your browser.

## Debugging

This is how it should look when the app is running and processing frames:

```
$ ss -tulpn | grep python
udp   UNCONN 0      0           10.124.0.4:55955      0.0.0.0:*    users:(("python",pid=5081,fd=11))
udp   UNCONN 0      0            10.48.0.7:56389      0.0.0.0:*    users:(("python",pid=5081,fd=10))
udp   UNCONN 0      0      146.190.169.113:57614      0.0.0.0:*    users:(("python",pid=5081,fd=9))
tcp   LISTEN 0      128            0.0.0.0:8443       0.0.0.0:*    users:(("python",pid=5081,fd=7))
tcp   LISTEN 0      128               [::]:8443          [::]:*    users:(("python",pid=5081,fd=6))
```

This should show the NAT type (ideally open):

```
$ sudo apt install stun-client
$ stun stun.l.google.com:19302
STUN client version 0.97
Primary: Open
Return value is 0x000001
```

- 0x000001: means "Success" and corresponds to an open NAT
- 0x000002: full cone NAT
- 0x000003: restricted cone NAT
- 0x000004: port restricted cone NAT
- 0x000005: symmetric NAT (which can cause issues with WebRTC)