from typing import Dict

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

def build_prompt(model: str) -> Dict:
    return {
        "model": model,
        "messages": [],
        "stream": False,
        "options": {
            "temperature": 1.0
        },
        "keep_alive": 20 * 60,  # 20 minutes
        "format": FORMAT,
        "images":[]
    }