# Chatbot Controller Robot Arm With Camera

**The goal is to build something to sort a bucket of lego into individual kits and make rebuilding them straight forward.**

1. I don't want to teach it how to do it - the chatbot must be smart
2. It can run for a week - I don't care as long as it sorts them
3. It can't require continuous input from me

Written in python, this project demonstrates how a chatbot can see and control a robot arm. 
The project runs completely offline.
The llama3.2-vision model is not yet smart enough to understand that their is nothing between the pincers, but it can move around on command.
Model evaluation is between 10 and 300 seconds with an old [Nvidia TESLA m40 24GB](https://www.techpowerup.com/gpu-specs/tesla-m40-24-gb.c3838).

**Turn up volume to hear conversation**

https://github.com/user-attachments/assets/b9038b2b-4e73-424a-8994-d9c9cfb3754c


# Technologies used
1. [6DOF Robotic Arm Kit from Amazon](https://amzn.to/4i77jRW)
1. [ESP32-CAM Webcam](https://amzn.to/4gTPbdn) flashed with [Webcam Software](https://RandomNerdTutorials.com/esp32-cam-video-streaming-web-server-camera-home-assistant/)
1. [USB to serial UART](https://amzn.to/3D4k00X) to control arm from PC (No dependency on this hardware)
1. [Ollama](https://www.ollama.com/) as the "offline" chatbot
1. GPU - I picked up a [Nvidia TESLA m40 24GB](https://ebay.us/tPNMRD) for $70 on ebay
1. [llama3.2-vision model](https://ollama.com/library/llama3.2-vision) as it accepts image input
1. [Text-To-Speach](https://github.com/nateshmbhat/pyttsx3#readme) to speak the chatbots' responses - runs offline
1. [Speach Recognition](https://github.com/Uberi/speech_recognition#readme) to listen for commands
1. Python3.11 (No dependency on this version)
1. Windows 10 (No dependency on this Platform)

# Next Steps
1. Evaluate online chatbots to speed up evaluation
1. Evaluate whether a second camera, and/or other angles helps chatbot understanding
1. Add interfaces to allow different hardware and APIs to be configured
1. Find a vision aware model that uses Ollamas newer "tools" interface

# Installation
```
git clone https://github.com/ribbles/ChatbotRobotArm/
cd ChatbotRobotArm
pip install -r requirements
```

# Testing
```
pytest
```

# Starting
```
python src/server.py
```

