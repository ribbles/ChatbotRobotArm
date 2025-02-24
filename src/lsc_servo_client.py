import logging
import serial
import struct
import time

from typing import List

# Obtained from Device Manager (Windows), lsusb (Linux)
COM_PORT_NAME = "Arduino Leonardo"


log = logging.getLogger("LSCServoController")


class LSCServoController:
    HEADER = [0x55, 0x55]  # Packet header
    BAUD_RATE = 9600

    # Command Constants
    CMD_SERVO_MOVE = 3
    CMD_ACTION_GROUP_RUN = 6
    CMD_ACTION_STOP = 7
    CMD_ACTION_SPEED = 11
    CMD_GET_BATTERY_VOLTAGE = 15
    CMD_MULT_SERVO_UNLOAD = 20
    CMD_MULT_SERVO_POS_READ = 21

    SERVO_LIMITS = {
        1: [1200, 1800],
        2: [500, 2500],
        3: [500, 2500],
        4: [500, 2500],
        5: [500, 2500],
        6: [500, 2500],
    }

    def __init__(self, port: str = "auto"):
        # https://pyserial.readthedocs.io/en/latest/pyserial_api.html
        if port is None or port == "auto":
            port = LSCServoController.detect_serial_port()
        self.ser = serial.Serial(port, self.BAUD_RATE, timeout=3, write_timeout=3)
        time.sleep(2)  # Allow time for serial to initialize

    @staticmethod
    def detect_serial_port() -> str:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        for port, desc, hwid in ports:
            if COM_PORT_NAME in desc:
                log.info("Found serial port %s %s", port, desc)
                return port
        raise Exception("Serial port not found")


    def send_command(self, command: int, params: list[int]):
        length = len(params) + 2  # Length includes command and length byte itself
        packet = self.HEADER + [length, command] + params
        # self.ser.reset_input_buffer()
        # self.ser.reset_output_buffer()
        bytes_written = self.ser.write(bytearray(packet))
        assert bytes_written == len(packet), f"{bytes_written} != {len(packet)}"
        self.ser.flush()

    def move_servo(self, servo_id: int, position: int, time_ms: int):
        assert servo_id in self.SERVO_LIMITS, f"{servo_id} not in {self.SERVO_LIMITS}"
        assert self.SERVO_LIMITS[servo_id][0] <= position >= self.SERVO_LIMITS[servo_id][0], f"For servo {servo_id}, {position} is outside of {self.SERVO_LIMITS[servo_id]}"
        params = [1, time_ms & 0xFF, (time_ms >> 8) & 0xFF,
                  servo_id, position & 0xFF, (position >> 8) & 0xFF]
        self.send_command(self.CMD_SERVO_MOVE, params)

    def move_servos(self, servo_ids: List[int], positions: List[int], time_ms: int):
        # servo count and time is fixed for all
        all_params = [len(servo_ids), time_ms & 0xFF, (time_ms >> 8) & 0xFF]
        assert len(servo_ids) == len(positions)
        for idx in range(0, len(servo_ids)):
            servo_id = servo_ids[idx]
            position = positions[idx]
            assert servo_id in self.SERVO_LIMITS, f"{servo_id} not in {self.SERVO_LIMITS}"
            assert self.SERVO_LIMITS[servo_id][0] <= position >= self.SERVO_LIMITS[servo_id][0], f"For servo {servo_id}, {position} is outside of {self.SERVO_LIMITS[servo_id]}"
            all_params.append(servo_id)
            all_params.append(position & 0xFF)
            all_params.append((position >> 8) & 0xFF)
        self.send_command(self.CMD_SERVO_MOVE, all_params)

    def run_action_group(self, group_id: int, times: int):
        params = [group_id, times & 0xFF, (times >> 8) & 0xFF]
        self.send_command(self.CMD_ACTION_GROUP_RUN, params)

    def stop_action_group(self) -> bool:
        self.send_command(self.CMD_ACTION_STOP, [])

    def set_action_speed(self, group_id: int, speed_percent: int) -> bool:
        params = [group_id, speed_percent & 0xFF, (speed_percent >> 8) & 0xFF]
        self.send_command(self.CMD_ACTION_SPEED, params)

    # def get_battery_voltage(self) -> int:
    #     packet = bytearray(self.HEADER + [2, self.CMD_GET_BATTERY_VOLTAGE])
    #     self.ser.reset_input_buffer()
    #     self.ser.reset_output_buffer()
    #     assert self.ser.write(packet) == len(packet)
    #     self.ser.flush()
    #     response = self.ser.read(4)  # Read expected response length
    #     if len(response) != 4:
    #         raise ValueError("Failed to get battery voltage: [%s]" % ", ".join(hex(n) for n in response))
    #     return response[2] | (response[3] << 8)

    def unload_servos(self, servo_ids: list[int]):
        params = [len(servo_ids)] + servo_ids
        self.send_command(self.CMD_MULT_SERVO_UNLOAD, params)

    def read_servo_positions(self, servo_ids: list[int] = list(SERVO_LIMITS.keys())) -> dict[int, int]:
        params = [len(servo_ids)] + servo_ids
        packet = bytearray(self.HEADER + [len(params) + 2, self.CMD_MULT_SERVO_POS_READ] + params)
        # self.ser.reset_input_buffer()
        # self.ser.reset_output_buffer()
        assert self.ser.write(packet) == len(packet)
        self.ser.flush()
        time.sleep(1)
        response = self.ser.read(len(self.HEADER) + 3 + 3 * len(servo_ids))
        if len(response) < 5:
            raise ValueError("Invalid response: [%s]" % ", ".join(hex(n) for n in response))
        positions = {}
        for i in range(len(servo_ids)):
            servo_id = response[len(self.HEADER) + 3 + i * 3]
            position = response[len(self.HEADER) + 5 + i * 3] | (response[len(self.HEADER) + 4 + i * 3] << 8)
            positions[servo_id] = position
        return positions

    def __del__(self):
        try:
            self.unload_servos(list(self.SERVO_LIMITS.keys()))
        except Exception:
            pass
        try:
            self.ser.close()
        except Exception:
            pass
