import requests
import random
import time
from datetime import datetime

# ================= CONFIGURACIÓN =================
URL_FIREBASE = "https://notificacion-fallos-default-rtdb.firebaseio.com/"
NODO = "Datos_Robot"

# Coordenadas base (Ecuador - Ibarra aprox)
BASE_LAT = 0.35830
BASE_LON = -78.11100

print("🟢 Simulador de datos Firebase iniciado (Ctrl + C para detener)")

while True:
    try:
        # -------- DATOS SIMULADOS --------
        BatV = round(random.uniform(3.6, 4.2), 3)           # Voltaje de batería
        latitud = round(BASE_LAT + random.uniform(-0.0002, 0.0002), 6)
        longitud = round(BASE_LON + random.uniform(-0.0002, 0.0002), 6)
        velocidad = round(random.uniform(0, 2.0), 2)       # m/s
        balanceo = round(random.uniform(0, 3), 2)       # Balanceo / roll
        voltaje = round(random.uniform(24,24.5), 2)     # Voltaje real del robot
        tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        datos = {
            "BatV": BatV,
            "Latitud": latitud,
            "Longitud": longitud,
            "Velocidad": velocidad,
            "Balanceo": balanceo,
            "Voltaje": voltaje,
            "Tiempo": tiempo
        }

        # -------- ENVÍO A FIREBASE --------
        r = requests.put(f"{URL_FIREBASE}{NODO}.json", json=datos)

        if r.status_code == 200:
            print(
                f"📡 BatV:{BatV}V | "
                f"Voltaje:{voltaje}V | "
                f"Lat:{latitud} | Lon:{longitud} | "
                f"Vel:{velocidad} m/s | "
                f"Balanceo:{balanceo}°"
            )
        else:
            print(f"❌ Error al enviar datos | Status code: {r.status_code}")

    except Exception as e:
        print("⚠️ Error:", e)

    time.sleep(2)
