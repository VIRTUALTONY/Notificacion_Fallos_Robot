import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
import serial
import struct

class TM171RollNode(Node):

    def __init__(self):
        super().__init__('tm171_roll_node')

        # Publicador de topic /tm171/roll
        self.publisher_ = self.create_publisher(Float32, 'tm171/roll', 10)

        # Serial: puerto y baudrate del TM171
        self.ser = serial.Serial("/dev/ttyACM0", 9600, timeout=1)

        # Timer: lee datos cada 50 ms (~20 Hz)
        self.timer = self.create_timer(0.05, self.read_roll)
        self.get_logger().info('TM171 roll node started')

    def leer_paquete(self):
        """Lee paquete completo del TM171 usando cabecera binaria"""
        while True:
            if self.ser.read(1) == b'\x14':
                if self.ser.read(1) == b'\x23':
                    if self.ser.read(1) == b'\x54':
                        if self.ser.read(1) == b'\x44':
                            payload = self.ser.read(24)
                            return payload

    def read_roll(self):
        try:
            payload = self.leer_paquete()
            roll = struct.unpack('<f', payload[5:9])[0]
            msg = Float32()
            msg.data = roll
            self.publisher_.publish(msg)
        except Exception as e:
            self.get_logger().warn(f'Error leyendo TM171: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = TM171RollNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()