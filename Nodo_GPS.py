import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, String
import serial
import pynmea2

PORT_GPS = "/dev/ttyUSB0"
BAUD_GPS = 9600


class GPSNode(Node):
    def __init__(self):
        super().__init__('gps')

        # Publicadores FLOAT32 (NO TOCAR)
        self.pub_lat = self.create_publisher(Float32, 'gps/lat', 10)
        self.pub_lon = self.create_publisher(Float32, 'gps/lon', 10)
        self.pub_vel = self.create_publisher(Float32, 'gps/vel', 10)

        # 🔹 NUEVO: status
        self.pub_status = self.create_publisher(String, 'gps/status', 10)

        try:
            self.ser = serial.Serial(PORT_GPS, BAUD_GPS, timeout=1)
            self.get_logger().info(f'GPS conectado en {PORT_GPS}')
        except Exception as e:
            self.get_logger().error(f'No se pudo abrir el GPS: {e}')
            self.ser = None

        # Variables de estado
        self.fix = 0
        self.sats = 0

        # ⏱️ AHORA CADA 1 SEGUNDO
        self.timer = self.create_timer(0.1, self.read_gps)

    def read_gps(self):
        if not self.ser:
            return

        try:
            line = self.ser.readline().decode('ascii', errors='ignore').strip()
            if not line:
                return

            # ===== STATUS (GGA) =====
            if line.startswith('$GPGGA'):
                msg = pynmea2.parse(line)
                self.fix = 1 if int(msg.gps_qual) > 0 else 0
                self.sats = int(msg.num_sats) if msg.num_sats else 0

            # ===== DATOS PRINCIPALES (RMC) =====
            elif line.startswith('$GPRMC'):
                msg = pynmea2.parse(line)

                if msg.status == 'A':  # FIX válido
                    lat = msg.latitude
                    lon = msg.longitude
                    vel = float(msg.spd_over_grnd) * 0.514444 if msg.spd_over_grnd else 0.0
                else:
                    lat = lon = vel = 0.0

                # Publicar FLOAT32
                self.pub_lat.publish(Float32(data=lat))
                self.pub_lon.publish(Float32(data=lon))
                self.pub_vel.publish(Float32(data=vel))

                # Publicar STATUS
                status_msg = String()
                status_msg.data = f"FIX={self.fix} SAT={self.sats}"
                self.pub_status.publish(status_msg)

        except pynmea2.ParseError:
            pass
        except Exception as e:
            self.get_logger().warn(f'Error GPS: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = GPSNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()