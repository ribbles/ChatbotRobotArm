import os
import faulthandler
import requests
import signal
import base64
import logging
from time import sleep
import json
from io import BytesIO
from PIL import Image
import pyttsx3
import speech_recognition as sr

from typing import Dict, List

from lsc_servo_client import LSCServoController


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",   # Green
        "WARNING": "\033[93m", # Yellow
        "ERROR": "\033[91m",   # Red
        "CRITICAL": "\033[95m" # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging():
    handler = logging.StreamHandler()
    formatter = ColorFormatter(
        "%(asctime)s.%(msecs)03d\t%(levelname)s\t%(name)s\t%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.handlers = [handler]
    logging.getLogger("connectionpool").setLevel(logging.DEBUG)


setup_logging()
log = logging.getLogger("RobotArm")
log.setLevel(logging.DEBUG)


ARM_SERIAL_PORT = "auto"
WEBCAM_URL = "http://10.0.0.27"
OLLAMA_URL = "http://10.0.0.205:11434/api/chat"
# OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_MODEL = "llama3.2-vision"


CHATBOT_INITIAL_PROMPT = """
You are controlling a 6DOF robotic arm and a webcam.
Every user request includes up to 4 webcam images in a mosaic to give you real-time visual context. 
Top-left is latest, followed by top-right, bottom-left & lower-right.
Use the images to inform how you move the arm.
Responses must be strictly formatted as JSON, structure as follows:
{
  "message": "Optional human-readable message for feedback.",  // the user will see this
  "tool_calls": [
    {
      "servo_id": 1,          // A number between 1 and 6 indicating the servo to move. 1 is the pincer.
      "position": 1500,       // A number between 500 and 2500 representing the target position, except servo 1 which is limited to the range 1200 to 1800.
    }
  ]
}
Guidelines:
- Each reponse creates a single arm movement, of 1 or more servos
- Both the "message" and "tool_calls" keys are optional
- If you include tool_calls, each tool_call object must have the fields servo_id & position
- You can include zero, one, or multiple tool_call objects in the tool_calls array
- Use the "message" field to summarise your actions and help rememeber what you have done.
Now, with the current webcam image in hand, please confirm that you are ready by executing an initial command.
For example, you might start by moving the arm slightly to signal readiness.
If you can't see the arm, please stop sending tool_calls and report as such in the message.
You should move the arm around to see which direction the servos move.
Ready? Please confirm that you can see the robot arm in the image, and move the arm.
"""

FORMAT = {
    "type": "object",
    "properties": {
        "message": {
            "type": "string",
        },
        "tool_calls": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                "servo_id": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 6,
                },
                "position": {
                    "type": "integer",
                    "minimum": 500,
                    "maximum": 2500,
                }
                },
                "required": [
                    "servo_id",
                    "position"
                ]
            }
        }
    }
}


def run():
    ollama_chat = None
    log.debug("Initializing Text-to-speech engine...")
    tts_engine = pyttsx3.init()
    log.debug("Initializing Speech-to-text engine...")
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        try:
            tts_engine.say("Robot Overlord beginning boot sequence.")
            tts_engine.runAndWait()

            log.debug("Initializing arm...")
            arm = LSCServoController(ARM_SERIAL_PORT)

            ollama_chat = build_prompt()
            user_prompt = CHATBOT_INITIAL_PROMPT
            while True:
                if user_prompt:
                    loop(arm, tts_engine, ollama_chat, user_prompt)
                tts_engine.say("What would you like me to do?")
                tts_engine.runAndWait()
                user_prompt = listen(source, recognizer)

        finally:
            try:
                ollama_chat["images"] = ["deleted"]
                log.info("ollama_chat log", extra={"data": ollama_chat})
            except Exception:
                pass
            try:
                tts_engine.stop()
            except Exception:
                pass
    
def loop(arm, tts_engine, ollama_chat: Dict, user_prompt: str):
    while True:
        # generate image
        IMAGE_HISTORY.append(fetch_image_from_url(WEBCAM_URL))
        ollama_chat["images"] = [build_image_montage()]
        # send prompt
        ollama_chat["messages"].append({"role":"user","content":user_prompt})
        response = chat(OLLAMA_URL, ollama_chat)
        log.debug("ollama response", extra={"data": response})
        # parse response
        message = response["message"]
        ollama_chat["messages"].append(message)
        content = json.loads(message["content"])
        # display and speak response
        log.warning("ROBOT: %s", content["message"])
        if content["message"]:
            tts_engine.say(content["message"])
            tts_engine.runAndWait()
        # validation
        if "tool_calls" not in content or len(content["tool_calls"]) == 0:
            log.info("No more commands. Exiting")
            return
        # command robot arm
        tool_calls = content["tool_calls"]
        log.warning("\tCommands")
        for tool_call in tool_calls:
            log.warning("\t\t%s", tool_call)
        send_commands_to_arm(arm, tool_calls)
        # since chatbot hasn't stopped sending commands, keep prompting for more
        user_prompt = "Here's the latest image from the webcam. Please continue..."

# base64 encoded
IMAGE_HISTORY: List[str] = []

def build_image_montage() -> str:
    images = [Image.open(BytesIO(base64.b64decode(img))) for img in IMAGE_HISTORY[-4:]]
    images.reverse()

    widths, heights = zip(*(img.size for img in images))
    new_width, new_height = max(widths) * 2, max(heights) * 2

    image = Image.new("RGB", (new_width, new_height))
    image.paste(images[0], (0, 0))
    if len(images) > 1:
        image.paste(images[1], (max(widths), 0))
    if len(images) > 2:
        image.paste(images[2], (0, max(heights)))
    if len(images) > 3:
        image.paste(images[3], (max(widths), max(heights)))

    output_buffer = BytesIO()
    image.save(output_buffer, format="JPEG")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image.save(os.path.join(current_dir, "image.jpg"))
    return base64.b64encode(output_buffer.getvalue()).decode('utf-8')

def fetch_image_from_url(url: str) -> str:
    with requests.get(url, stream=True, timeout=5) as response:
        response.raise_for_status()

        buffer = b""
        content_started = False

        for chunk in response.iter_content(chunk_size=1024):
            if not content_started:
                if b"\r\n\r\n" in chunk:  # Detect end of HTTP headers
                    chunk = chunk.split(b"\r\n\r\n", 1)[1]  # Strip headers
                    content_started = True
                else:
                    continue  # Skip until headers are gone

            buffer += chunk
            if b"\xff\xd9" in buffer:  # JPEG end marker
                break

    image_data = buffer[:buffer.index(b"\xff\xd9") + 2]
    return base64.b64encode(image_data).decode('utf-8')

def build_prompt() -> Dict:
    return {
        "model": OLLAMA_MODEL,
        "messages": [],
        "stream": False,
        "options": {
            "temperature": 1.0
        },
        "keep_alive": 20 * 60,  # 20 minutes
        "format": FORMAT,
        "images":[]
    }

def chat(url: str, prompt: Dict) -> Dict:
    try:
        response = requests.post(url, json=prompt, timeout=300)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log.exception("Exception getting camera image")
        if isinstance(e, requests.exceptions.HTTPError):
            log.debug("Request Headers:", e.response.request.headers)
            log.debug("Request Body:", e.response.request.body[0:100])
            log.debug("Response Headers:", e.response.headers)
            log.debug("Response Body:", e.response.text[0:100])
        raise 

def send_commands_to_arm(arm: LSCServoController, commands: List[Dict]):
    servo_ids = []
    positions = []

    for cmd in commands:
        assert 1 <= cmd["servo_id"] <= 6, cmd["servo_id"]
        assert 500 <= cmd["position"] <= 2500, cmd["position"]
        assert cmd["servo_id"] != 1 or 1200 <= cmd["position"] <= 1800, cmd["position"]
        servo_ids.append(cmd["servo_id"])
        positions.append(cmd["position"])
    arm.move_servos(servo_ids, positions, 2000)
    try:
        log.info("servo positions:", arm.read_servo_positions())
    except Exception as e:
        log.debug("Error getting servo positions")

def listen(source, recognizer) -> str:
    # return "Pick up the die"
    """Capture speech and convert it to text."""
    recognizer.adjust_for_ambient_noise(source)  # Adjust to background noise
    try:
        log.debug("Listening...")
        audio = recognizer.listen(source, timeout=10)  # Listen for 5 seconds
        text = recognizer.recognize_google(audio)  # Convert speech to text
        log.warning("Heard: %s", text)
        return text
    except sr.UnknownValueError:
        log.warning("I didn't understand.", exc_info=True)
        return None
    except sr.RequestError:
        log.exception("Speech recognition service unavailable.")
        raise

if __name__ == "__main__":
    run()


