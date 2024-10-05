# webrtc-bot

## Setup

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
   pip install aiohttp aiortc opencv-python-headless numpy
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