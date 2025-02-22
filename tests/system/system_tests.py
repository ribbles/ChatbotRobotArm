import time
import unittest
from lsc_servo_client import LSCServoController  # Adjust import as needed
from random import randint


# Set the correct serial port
SERIAL_PORT = "COM9"  # Change to actual port (e.g., "COM3" on Windows)


class TestLSCServoControllerSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up the real serial connection once for all tests."""
        cls.controller = LSCServoController(SERIAL_PORT)
        time.sleep(2)  # Allow time for initialization

    # def test_get_battery_voltage(self):
    #     """Test retrieving battery voltage."""
    #     # Arrange
    #     expected_min_voltage = 1000  # Assuming minimum operational voltage is 6V
    #     expected_max_voltage = 9000  # Assuming max is 9V

    #     # Act
    #     voltage = self.controller.get_battery_voltage()

    #     # Assert
    #     self.assertGreaterEqual(voltage, expected_min_voltage, "Voltage too low!")
    #     self.assertLessEqual(voltage, expected_max_voltage, "Voltage too high!")
    #     print(f"Battery Voltage: {voltage} mV")

    def test_move_servos(self):
        for servo_id in range(1, 6):
            with self.subTest(servo_id=servo_id):
                # Arrange
                min = self.controller.SERVO_LIMITS[servo_id][0]
                max = self.controller.SERVO_LIMITS[servo_id][1]
                position = randint(min, max)  # Example position forward
                time_ms = 2000

                # Act
                self.controller.move_servo(servo_id, position, time_ms)

                # Assert
                # assert self.controller.read_servo_positions([servo_id])[0] == position
        time.sleep(2)
        for servo_id in range(1, 6):
            with self.subTest(servo_id=servo_id):
                # Arrange
                position = 1500  # Example position forward
                time_ms = 2000

                # Act
                self.controller.move_servo(servo_id, position, time_ms)

                # Assert
                # assert self.controller.read_servo_positions([servo_id])[0] == position
        time.sleep(2)

    # def test_read_servo_position(self):
    #     """Test reading the servo position."""
    #     for servo_id in range(1, 6):
    #         with self.subTest(servo_id=servo_id):
    #             # Arrange
    #             min = self.controller.SERVO_LIMITS[servo_id][0]
    #             max = self.controller.SERVO_LIMITS[servo_id][1]
    #             # Act
    #             positions = self.controller.read_servo_positions([servo_id])

    #             # Assert
    #             self.assertIn(servo_id, positions, "Servo ID not found in response!")
    #             print(f"Servo {servo_id} Position: {positions[servo_id]}")
    #             assert min >= positions[servo_id] >= max

    def test_unload_servo(self):
        """Test unloading the servo."""
        # Arrange
        servo_id = 1

        # Act
        self.controller.unload_servos([servo_id])
        
        # Assert

    @classmethod
    def tearDownClass(cls):
        """Cleanup after tests."""
        print("System tests complete.")


if __name__ == "__main__":
    unittest.main()
