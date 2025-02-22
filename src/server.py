import faulthandler
import requests
import signal
import base64
from time import sleep
import json
from io import BytesIO
from PIL import Image
import pyttsx3
import speech_recognition as sr

from typing import Dict, List

from lsc_servo_client import LSCServoController


# faulthandler.enable()
# faulthandler.register(signal.SIGINT)


ARM_SERIAL_PORT = "auto"
WEBCAM_URL = "http://10.0.0.27"
OLLAMA_URL = "http://10.0.0.205:11434/api/chat"
# OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_MODEL = "llama3.2-vision"


CHATBOT_INITIAL_PROMPT = """
You are controlling a 6DOF robotic arm that has 6 servos and a webcam.
Every user request includes the latest webcam image (even if the request text is empty) to give you real-time visual context of where the arm moved to.
Use that image to inform how you move the arm next.
Your responses must be strictly formatted as JSON. The JSON structure is defined as follows:
{
  "message": "Optional human-readable message for feedback.",  // the user will see this
  "tool_calls": [
    {
      "servo_id": 1,          // A number between 1 and 6 indicating the servo to move. 1 is the pincer.
      "position": 1500,       // A number between 500 and 2500 representing the target position, except servo 1 which is limited to the range 1200 to 1800.
      "time_ms": 1000         // Time in milliseconds for the move to complete. Please keep your movements between 1-5 seconds.
    }
  ]
}
Guidelines:
- Both the "message" and "tool_calls" keys are optional.
- If you include tool_calls, each tool_call object must have the fields: servo_id, position, and time_ms.
- You can include zero, one, or multiple tool_call objects in the tool_calls array.
- Your output must not include any extra text or formatting outside of valid JSON.
I suggest that the response message comment on how the arm moved so you remember which way each servo moves.
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
                },
                "time_ms": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 5000,
                }
                },
                "required": [
                    "servo_id",
                    "position",
                    "time_ms"
                ]
            }
        }
    }
}


def run():
    """
        1. Ask user for prompt
        1. Capture image
        1. Send prompt & image to chatbot
        1. Recieve response from chatbot
        1. Forward message to user
        1. Forward commands to robot
        1. Capture errors from commands for next prompt
        1. Repeat
    """
    ollama_chat = None
    print("Initialize text-to-speech engine...")
    tts_engine = pyttsx3.init()
    try:
        tts_engine.say("Robot Overlord beginning boot sequence.")
        tts_engine.runAndWait()
        print("Done.")
        print("")

        print("Initializing camera...")
        image = fetch_image_from_url(WEBCAM_URL)
        print("Image acquired with size ", len(image), " bytes starting with: " , image[0:20], " and ending with ", image[-20:])
        print()

        print("Initializing arm...")
        arm = LSCServoController(ARM_SERIAL_PORT)
        print("Done.")
        print("")

        print("Initializing chatbot...")
        ollama_chat = build_prompt(CHATBOT_INITIAL_PROMPT, image)
        response = chat(OLLAMA_URL, ollama_chat)
        message = response["message"]
        ollama_chat["messages"].append(message)
        content = json.loads(message["content"])
        print("ROBOT: ", content["message"])
        tts_engine.say(content["message"])
        tts_engine.runAndWait()
        if "tool_calls" not in content or len(content["tool_calls"]) == 0:
            print("No more commands. Exiting.... details:", content)
            return
        tool_calls = content["tool_calls"]
        print("\t\tCommands:")
        for tool_call in tool_calls:
            print("\t\t\t", tool_call)
        send_commands_to_arm(arm, tool_calls)
        print("Done.")
        print("")

        while True:
            tts_engine.say("What would you like me to do?")
            tts_engine.runAndWait()
            user_prompt = listen()
            loop(arm, tts_engine, ollama_chat, user_prompt)

    finally:
        ollama_chat["images"] = ["deleted"]
        print("ollama_chat:", json.dumps(ollama_chat))
        tts_engine.stop()
    
def loop(arm, tts_engine, ollama_chat: Dict, user_prompt: str):
    while True:
        ollama_chat["images"] = [fetch_image_from_url(WEBCAM_URL)]
        ollama_chat["messages"].append({"role":"user","content":user_prompt})
        response = chat(OLLAMA_URL, ollama_chat)
        message = response["message"]
        ollama_chat["messages"].append(message)
        content = json.loads(message["content"])
        print("ROBOT: ", content["message"])
        if content["message"]:
            tts_engine.say(content["message"])
            tts_engine.runAndWait()
        if "tool_calls" not in content or len(content["tool_calls"]) == 0:
            print("No more commands. Exiting.... details:", content)
            return
        tool_calls = content["tool_calls"]
        print("\t\tCommands:")
        for tool_call in tool_calls:
            print("\t\t\t", tool_call)
        send_commands_to_arm(arm, tool_calls)
        user_prompt = "Here's the latest image from the webcam. Please continue..."

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

    # Validate image integrity
    try:
        img = Image.open(BytesIO(image_data))
        img.verify()  # Will raise an error if the image is corrupt
    except Exception as e:
        raise RuntimeError(f"Incomplete or corrupt image received: {e}") from e

    return base64.b64encode(image_data).decode('utf-8')

def build_prompt(prompt: str, base64_image: str) -> Dict:
    return {
        "model": OLLAMA_MODEL,
        "messages": [{"role":"user","content":prompt}],
        "stream": False,
        "keep_alive": 20 * 60,  # 20 minutes
        "format": FORMAT,
        "images":[base64_image]
    }

def chat(url: str, prompt: Dict) -> Dict:
    try:
        response = requests.post(url, json=prompt, timeout=300)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if isinstance(e, requests.exceptions.HTTPError):
            print("Request Headers:", e.response.request.headers)
            print("Request Body:", e.response.request.body[0:100])
            print("Response Headers:", e.response.headers)
            print("Response Body:", e.response.text[0:100])
        raise 

def send_commands_to_arm(arm: LSCServoController, commands: List[Dict]):
    servo_ids = []
    positions = []
    time_mss = []
    for cmd in commands:
        assert 1 <= cmd["servo_id"] <= 6
        assert 500 <= cmd["position"] <= 2500
        assert cmd["servo_id"] != 1 or 1200 <= cmd["position"] <= 1800
        assert 1000 <= cmd["time_ms"] <= 5000
        servo_ids.append(cmd["servo_id"])
        positions.append(cmd["position"])
        time_mss.append(cmd["time_ms"])
    arm.move_servos(servo_ids, positions, max(time_mss))

def listen() -> str:
    # return "Pick up the die"
    """Capture speech and convert it to text."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source)  # Adjust to background noise
        try:
            audio = recognizer.listen(source, timeout=5)  # Listen for 5 seconds
            text = recognizer.recognize_google(audio)  # Convert speech to text
            print("Heard: ", text)
            return text
        except sr.UnknownValueError:
            print("I didn't understand.")
            return listen()
        except sr.RequestError:
            print("Speech recognition service unavailable.")
            raise

if __name__ == "__main__":
    run()


