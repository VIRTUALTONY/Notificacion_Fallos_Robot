#include <SoftwareSerial.h>

SoftwareSerial secondSerial(2, 3); // RX, TX

// ===== BUFFERS DE 10 CARACTERES =====
char latitud[11]      = "0000000000";
char longitud[11]     = "0000000000";
char velocidad[11]    = "0000000000";
char balanceo[11]     = "0000000000";

char voltaje[11]          = "0000000000";
char pic_max_volt[11]     = "0000000000";
char pic_min_volt[11]     = "0000000000";
char max_der_lat[11]      = "0000000000";
char max_der_lon[11]      = "0000000000";
char max_der_vel[11]      = "0000000000";

// ===== VOLTAJE =====
const int pinSensor = A0;
const float R1 = 82000.0;
const float R2 = 10000.0;

float vMax = 0.0;
float vMin = 99.0;

// ===== DERIVADAS =====
float lastLat = 0, lastLon = 0, lastVel = 0;
float maxDerLat = 0, maxDerLon = 0, maxDerVel = 0;
unsigned long lastDerTime = 0;

// ===== TIEMPOS =====
unsigned long ventanaInicio = 0;
const unsigned long ventana = 10000;

// ===== TRIGGER =====
const int triggerPin = 13;
unsigned long previousMillis = 0;
const unsigned long interval = 15000;
const unsigned long pulseDuration = 100;

void setup() {
  Serial.begin(9600);
  secondSerial.begin(9600);

  pinMode(triggerPin, OUTPUT);
  digitalWrite(triggerPin, LOW);

  ventanaInicio = millis();
  lastDerTime = millis();
}

void loop() {

  // ===== RECEPCIÓN ROS =====
  if (Serial.available()) {
    String linea = Serial.readStringUntil('\n');
    linea.trim();

    int c1 = linea.indexOf(',');
    int c2 = linea.indexOf(',', c1 + 1);
    int c3 = linea.indexOf(',', c2 + 1);

    if (c1 != -1 && c2 != -1 && c3 != -1) {
      linea.substring(0, c1).toCharArray(latitud, 11);
      linea.substring(c1 + 1, c2).toCharArray(longitud, 11);
      linea.substring(c2 + 1, c3).toCharArray(velocidad, 11);
      linea.substring(c3 + 1).toCharArray(balanceo, 11);
    }
  }

  // ===== CÁLCULO VOLTAJE =====
  float vActual = leerVoltajeReal();
  if (vActual > vMax) vMax = vActual;
  if (vActual < vMin && vActual > 5.0) vMin = vActual;

  // ===== DERIVADAS =====
  unsigned long ahora = millis();
  float dt = (ahora - lastDerTime) / 1000.0;

  if (dt > 0) {
    float lat = atof(latitud);
    float lon = atof(longitud);
    float vel = atof(velocidad);

    float dLat = (lat - lastLat) / dt;
    float dLon = (lon - lastLon) / dt;
    float dVel = (vel - lastVel) / dt;

    if (dLat > maxDerLat) maxDerLat = dLat;
    if (dLon > maxDerLon) maxDerLon = dLon;
    if (dVel > maxDerVel) maxDerVel = dVel;

    lastLat = lat;
    lastLon = lon;
    lastVel = vel;
    lastDerTime = ahora;
  }

  // ===== CIERRE DE VENTANA 10s =====
  if (ahora - ventanaInicio >= ventana) {
    ventanaInicio = ahora;

    formatFloat(vActual, voltaje);
    formatFloat(vMax, pic_max_volt);
    formatFloat(vMin, pic_min_volt);
    formatFloat(maxDerLat, max_der_lat);
    formatFloat(maxDerLon, max_der_lon);
    formatFloat(maxDerVel, max_der_vel);

    maxDerLat = maxDerLon = maxDerVel = 0.0;
    vMax = 0.0;
    vMin = 99.0;
  }

  // ===== RESPUESTAS LORA =====
  if (secondSerial.available()) {
    char cmd = secondSerial.read();
    switch (cmd) {
      case '1': secondSerial.print(latitud);      break;
      case '2': secondSerial.print(longitud);     break;
      case '3': secondSerial.print(velocidad);    break;
      case '4': secondSerial.print(balanceo);     break;
      case '5': secondSerial.print(voltaje);      break;
      case '6': secondSerial.print(pic_max_volt); break;
      case '7': secondSerial.print(pic_min_volt); break;
      case '8': secondSerial.print(max_der_lat);  break;
      case '9': secondSerial.print(max_der_lon);  break;
      case 'A': secondSerial.print(max_der_vel);  break;
      default:  secondSerial.print("CMD_ERR");    break;
    }
  }

  // ===== TRIGGER =====
  if (ahora - previousMillis >= interval) {
    previousMillis = ahora;
    digitalWrite(triggerPin, HIGH);
    delay(pulseDuration);
    digitalWrite(triggerPin, LOW);
  }
}

// ===== FUNCIONES =====
float leerVoltajeReal() {
  long suma = 0;
  for (int i = 0; i < 100; i++) {
    suma += analogRead(pinSensor);
    delay(1);
  }
  float promedio = suma / 100.0;

  // Voltaje que llega al A0
  float vPin = (promedio * 5.0) / 1023.0;

  // ⭐ CONVERSIÓN QUE PEDISTE
  float vReal = (vPin * 10.0) - 2.0;

  return vReal;
}

// ===== FORMATO SIN ESPACIOS (RELLENO CON CEROS) =====
void formatFloat(float valor, char *buffer) {
  char temp[12];
  dtostrf(valor, 10, 5, temp);

  for (int i = 0; i < 10; i++) {
    if (temp[i] == ' ') temp[i] = '0';
    buffer[i] = temp[i];
  }
  buffer[10] = '\0';
}