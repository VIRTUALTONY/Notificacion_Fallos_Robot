import requests
import sqlite3
import time

# ===== CONFIG FIREBASE =====
FIREBASE_URL = "https://notificacion-fallos-default-rtdb.firebaseio.com/Datos_Robot.json"

# ===== CONFIG SQLITE =====
DB_FILE = "C:/Users/ASUS/Desktop/interfaz tesis/base de datos/notificaciones.db3"

# Conectar SQLite
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

print("🔥 Conexión SQLite lista. Iniciando lectura de Firebase...")

while True:
    try:
        # Leer datos de Firebase
        response = requests.get(FIREBASE_URL, timeout=5)
        data = response.json()

        if not data:
            print("Firebase vacío")
            time.sleep(5)
            continue

        # Extraer datos
        latitud = data.get("Latitud", 0.0)
        longitud = data.get("Longitud", 0.0)
        velocidad = data.get("Velocidad", 0.0)
        balanceo = data.get("Balanceo", 0.0)
        voltaje = data.get("Voltaje", 0.0)

        # 🔹 Verificar duplicados
        cursor.execute("""
        SELECT 1 FROM notificacion 
        WHERE Latitud=? AND Longitud=? AND Velocidad=? AND Balanceo=? AND Voltaje=?
        """, (latitud, longitud, velocidad, balanceo, voltaje))
        exists = cursor.fetchone()

        if exists:
            print("⚠ Registro duplicado, no se guarda")
        else:
            # Insertar en SQLite
            cursor.execute("""
            INSERT INTO notificacion (Latitud, Longitud, Velocidad, Balanceo, Voltaje)
            VALUES (?, ?, ?, ?, ?)
            """, (latitud, longitud, velocidad, balanceo, voltaje+1.2))
            conn.commit()
            print(f"✔ Datos insertados: Lat={latitud}, Lon={longitud}, Vel={velocidad}, Bal={balanceo}, Volt={voltaje+1.2}")

    except Exception as e:
        print("❌ Error:", e)

    time.sleep(7)  # espera 5 segundos antes de leer otra vez
