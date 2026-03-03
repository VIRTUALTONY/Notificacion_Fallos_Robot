#!/usr/bin/env python3

import time
import mysql.connector
from mysql.connector import Error
from firebase import firebase
from datetime import datetime

# 🔥 Firebase
urlDB = 'https://notificacion-fallos-default-rtdb.firebaseio.com/'
nombreDispositivo = 'Datos_Robot'

# -------------------------------------------------------------------
# ENVIAR DATOS A FIREBASE
# -------------------------------------------------------------------
def sendData(usuario, data):
    fb = firebase.FirebaseApplication(urlDB, None)
    result = fb.patch('/' + usuario + '/', data)
    return result

# -------------------------------------------------------------------
# LEER SOLO TU DISPOSITIVO DESDE MYSQL
# -------------------------------------------------------------------
def connectMySQL():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='Robot',
            user='xibernetiq',
            password='Automatica0123@'
        )

        if connection.is_connected():
            cursor = connection.cursor()

            cursor.execute("""
                SELECT BatV, latitud, longitud, velocidad, balanceo, voltaje, received_at 
                FROM Robot 
                WHERE device_id = 'rs485-lb-robot'
                ORDER BY id DESC LIMIT 1
            """)

            return cursor.fetchone()

    except Error as e:
        print("❌ Error en MySQL:", e)
        return None

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# -------------------------------------------------------------------
# OBTENER FECHA FORMATEADA
# -------------------------------------------------------------------
def readTime():
    return datetime.now().strftime("%d %b %Y %H:%M:%S")

# -------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# -------------------------------------------------------------------
if __name__ == '__main__':
    lastData = None

    while True:
        data = connectMySQL()

        if data and data != lastData:
            lastData = data

            BatV, latitud, longitud, velocidad, balanceo, voltaje, received_at = data

            firebaseData = {
                'BatV': BatV,
                'Latitud': latitud,
                'Longitud': longitud,
                'Velocidad': velocidad,
                'Balanceo': balanceo,   # antes Roll
                'Voltaje': voltaje,     # nuevo
                'Tiempo': received_at.strftime("%d %b %Y %H:%M:%S") if received_at else readTime()
            }

            try:
                result = sendData(nombreDispositivo, firebaseData)
                print("✅ Enviado a Firebase:", result)
            except Exception as e:
                print("❌ Error enviando a Firebase:", e)

        time.sleep(2)  # espera 2s antes de leer nuevamente
