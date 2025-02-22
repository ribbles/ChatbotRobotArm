import unittest
from unittest.mock import MagicMock, patch
import serial
from lsc_servo_client import LSCServoController  # Adjust import as needed


class TestLSCServoController(unittest.TestCase):
    @patch("serial.Serial")
    def setUp(self, mock_serial):
        """Setup the mocked serial connection for each test."""
        self.mock_serial_instance = mock_serial.return_value
        self.controller = LSCServoController("/dev/ttyUSB0")

    def test_send_command_success(self):
        """Test if send_command sends the correct data and reads a valid response."""
        # Arrange
        self.mock_serial_instance.read.return_value = bytearray([0x55, 0x55])
        expected_packet = bytearray([0x55, 0x55, 8, 3, 1, 0xE8, 0x03, 1, 0xD0, 0x07])
        self.mock_serial_instance.write.return_value = len(expected_packet)

        # Act
        self.controller.send_command(3, [1, 0xE8, 0x03, 1, 0xD0, 0x07])

        # Assert
        self.mock_serial_instance.write.assert_called_with(expected_packet)

    def test_move_servo(self):
        """Test move_servo function with a valid response."""
        # Arrange
        self.mock_serial_instance.read.return_value = bytearray([0x55, 0x55])
        expected_packet = bytearray([0x55, 0x55, 8, 3, 1, 0xE8, 0x03, 1, 0xD0, 0x07])
        self.mock_serial_instance.write.return_value = len(expected_packet)

        # Act
        self.controller.move_servo(1, 2000, 1000)

        # Assert
        self.mock_serial_instance.write.assert_called_with(expected_packet)

    # def test_get_battery_voltage(self):
    #     """Test getting battery voltage with a valid response."""
    #     # Arrange
    #     self.mock_serial_instance.read.return_value = bytearray([0x55, 0x55, 0x34, 0x12])  # 0x1234 = 4660mV
    #     self.mock_serial_instance.write.return_value = 4

    #     # Act
    #     voltage = self.controller.get_battery_voltage()

    #     # Assert
    #     self.assertEqual(voltage, 4660)

    # def test_read_servo_positions(self):
    #     """Test reading servo positions for a single servo."""
    #     # send: [0x55, 0x55, 0x09, 0x15, 0x06, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06]
    #     # recv: [0x55, 0x55, 0x15, 0x15, 0x06, 0x01, 0x01, 0xF4, 0x02, 0x01, 0xF4, 0x03, 0x01, 0xF4, 0x04, 0x01, 0xF4, 0x05, 0x01, 0xF4, 0x06, 0x01, 0xF4]
    #     # Arrange
    #     self.mock_serial_instance.read.return_value = bytearray([0x55, 0x55, 0x15, 0x15, 0x06, 0x01, 0x01, 0xF4, 0x02, 0x01, 0xF4, 0x03, 0x01, 0xF4, 0x04, 0x01, 0xF4, 0x05, 0x01, 0xF4, 0x06, 0x01, 0xF4])
    #     expected_positions = {1: 500, 2: 500, 3: 500, 4: 500, 5: 500, 6: 500}
    #     self.mock_serial_instance.write.return_value = 11

    #     # Act
    #     positions = self.controller.read_servo_positions([1, 2, 3, 4, 5, 6])

    #     # Assert
    #     self.assertEqual(positions, expected_positions)

    def test_unload_servos(self):
        """Test unloading multiple servos with a valid response."""
        # send: [0x55, 0x55, 0x06, 0x14, 0x03, 0x01, 0x02, 0x03]
        # recv: [0x55, 0x55, 0x09, 0x14, 0x06, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06]
        # Arrange
        self.mock_serial_instance.read.return_value = bytearray([0x55, 0x55, 0x09, 0x14, 0x06, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06])
        expected_packet = bytearray([0x55, 0x55, 0x06, 0x14, 0x03, 0x01, 0x02, 0x03])
        self.mock_serial_instance.write.return_value = len(expected_packet)

        # Act
        self.controller.unload_servos([1, 2, 3])

        # Assert
        self.mock_serial_instance.write.assert_called_with(expected_packet)

    def test_example1(self):
        # in: 0x55 0x55 0x08 0x03 0x01 0xE8 0x03 0x01 0xD0 0x07
        # out: 0x55 0x55 0x0B 0x03 0x02 0x20 0x03 0x02 0xB0 0x04 0x090xFC0x08
        # Arrange
        self.mock_serial_instance.read.return_value = bytearray([0x55, 0x55, 0x0B, 0x03, 0x02, 0x20, 0x03, 0x02, 0xB0, 0x04, 0x09, 0xFC, 0x08])
        expected_packet = bytearray([0x55, 0x55, 0x08, 0x03, 0x01, 0xE8, 0x03, 0x01, 0xD0, 0x07])
        self.mock_serial_instance.write.return_value = len(expected_packet)

        # Act
        self.controller.move_servo(1, 2000, 1000)

        # Assert
        self.mock_serial_instance.write.assert_called_with(expected_packet)



if __name__ == "__main__":
    unittest.main()
