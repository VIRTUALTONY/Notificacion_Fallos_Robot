import tkinter as tk
from tkinter import Canvas, messagebox, Toplevel
import requests
import time
import threading
from collections import deque
import platform
from plyer import notification
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkintermapview
import sqlite3
import os
# ---------------- FIREBASE ----------------
urlDB = 'https://notificacion-fallos-default-rtdb.firebaseio.com/'
nombreDispositivo = 'Datos_Robot'

#    LEER DATOS SQLITE
# Diccionario de explicaciones de errores
ERRORS_INFO = {
    "BAL-01": ("POSIBLE CAÍDA POR INERCIA", "El robot se está inclinando demasiado. Revisar inclinación y trayectoria."),
    "BAL-02": ("SOBREESFUERZO EN LOS MOTORES", "Los motores están trabajando demasiado. Verificar balanceo y límites."),
    "BAL-03": ("EL ROBOT SE CAYÓ", "El robot se volcó. Enviar a un operador a revisar inmediatamente."),
    "VOL-01": ("SOBREVOLTAJE DETECTADO", "El voltaje ha superado 3.1V. Posible riesgo de daño al robot."),
    "VOL-02": ("BATERÍA BAJA", "El voltaje está por debajo de 2V. Cargar o reemplazar batería.")
}
class RobotStatusApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Estado del Robot")
        self.root.geometry("1000x780")

        # ---------------- MENÚ ----------------
        menu_frame = tk.Frame(root)
        menu_frame.pack(side="left", fill="y", padx=10, pady=10)

        tk.Label(menu_frame, text="🔹 Menú Principal 🔹", font=("Arial", 16, "bold")).pack(pady=20)
        tk.Button(menu_frame, text="Balanceo", font=("Arial", 14), width=18, height=2,
                  command=lambda: self.show_frame("balanceo")).pack(pady=10)
        tk.Button(menu_frame, text="GPS", font=("Arial", 14), width=18, height=2,
                  command=lambda: self.show_frame("gps")).pack(pady=10)
       
        tk.Button(menu_frame, text="Voltaje", font=("Arial", 14), width=18, height=2,
                  command=lambda: self.show_frame("voltaje")).pack(pady=10)


# Contenedor para LED y Botón Reset
        led_reset_frame = tk.Frame(menu_frame)
        led_reset_frame.pack(pady=5)

        self.voltaje_led_canvas = Canvas(led_reset_frame, width=80, height=80)
        self.voltaje_led_canvas.pack(side="left")
        self.voltaje_led = self.voltaje_led_canvas.create_oval(10, 10, 70, 70, fill="grey")

        # BOTÓN RESET
        self.btn_reset = tk.Button(
            led_reset_frame, 
            text="RESET", 
            font=("Arial", 10, "bold"),
            bg="lightgrey",
            command=self.reset_alerta_manual
        )
        self.btn_reset.pack(side="left", padx=10)
        self.reset_temporal = False  # bandera que indica que estamos en espera de 15s



      ## LABEL

        self.voltaje_led_label = tk.Label(
            menu_frame,
            width=30,
            height=15,
            bg="white",
            relief="ridge"
        )
        self.voltaje_led_label.pack(pady=5)
        # Inicia la actualización automática del label con datos de SQLite
        self.actualizar_label_sqlite()


        tk.Button(
            menu_frame, 
            text="GUARDAR DATOS", 
            font=("Arial", 10), 
            width=18, height=2,
            command=self.guardar_en_txt  # Esto busca la función abajo
        ).pack(pady=10)
        
        # ---------------- CONTENEDORES ----------------
        self.frames = {}
        container = tk.Frame(root)
        container.pack(side="right", fill="both", expand=True)

        # ---------------- DATOS ----------------
        self.balanceo_data = deque(maxlen=50)
        self.lat_data = deque(maxlen=50)
        self.lon_data = deque(maxlen=50)
        self.voltaje_data = deque(maxlen=50)

        self.CENTER_LAT = 0.35852
        self.CENTER_LON = -78.1111
        self.DEG_PER_KM = 0.009
        self.positions = []
        self.square_path = None
        self.trajectory_path = None
# <--- AGREGA LA LÍNEA JUSTO AQUÍ --->
        self.historial_alertas = []
        self.last_alert_state = None

        # ---------------- FRAMES ----------------
        self.create_balanceo_frame(container)
        self.create_gps_frame(container)
        self.create_error_frame(container)
        self.create_voltaje_frame(container)

        self.show_frame("balanceo")

        threading.Thread(target=self.update_status, daemon=True).start()

    # ---------------- MOSTRAR FRAME ----------------
    def show_frame(self, name):
        for key, frame in self.frames.items():
            frame.pack_forget()
        self.frames[name].pack(fill="both", expand=True)

    # ---------------- BALANCEO ----------------
    def create_balanceo_frame(self, container):
        frame = tk.Frame(container)
        self.frames["balanceo"] = frame

        tk.Label(frame, text="🔹 Balanceo del Robot 🔹", font=("Arial", 14, "bold")).pack(pady=10)

        led_frame = tk.Frame(frame)
        led_frame.pack(pady=5)
        self.canvas_balanceo = Canvas(led_frame, width=80, height=80)
        self.canvas_balanceo.pack(side="left", padx=10)
        self.balanceo_led = self.canvas_balanceo.create_oval(20, 20, 60, 60, fill="grey")
        self.balanceo_status = tk.Label(led_frame, text="Estado Balanceo", fg="red", font=("Arial", 11))
        self.balanceo_status.pack(side="left", padx=10)

        main_frame = tk.Frame(frame)
        main_frame.pack(fill="both", expand=True, pady=10)

        # Gráfico
        graph_frame = tk.Frame(main_frame)
        graph_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        self.fig_balanceo, self.ax_balanceo = plt.subplots(figsize=(4.5,3))
        self.ax_balanceo.set_title("Balanceo (°)")
        self.ax_balanceo.set_xlabel("Tiempo (muestras)")
        self.ax_balanceo.set_ylabel("Ángulo")
        self.ax_balanceo.grid(True)
        self.balanceo_line, = self.ax_balanceo.plot([], [], label="Balanceo", color="blue")
        self.lower_line, = self.ax_balanceo.plot([], [], '--', color="red", label="Límite inferior")
        self.upper_line, = self.ax_balanceo.plot([], [], '--', color="red", label="Límite superior")
        self.ax_balanceo.axhline(0, color='black', linewidth=1)
        self.ax_balanceo.legend(fontsize=8)
        self.fig_balanceo.tight_layout()
        self.balanceo_canvas_widget = FigureCanvasTkAgg(self.fig_balanceo, master=graph_frame)
        self.balanceo_canvas_widget.get_tk_widget().pack(fill="both", expand=True)

        # Sliders
        sliders_frame = tk.Frame(main_frame)
        sliders_frame.pack(side="left", padx=10, pady=10, fill="y")
        tk.Label(sliders_frame, text="Límite +", font=("Arial",10)).pack(pady=(0,5))
        self.upper_alert = tk.DoubleVar(value=30)
        tk.Scale(sliders_frame, from_=180, to=0, orient="vertical",
                 variable=self.upper_alert, length=150, resolution=1).pack(pady=5)
        tk.Label(sliders_frame, text="Límite -", font=("Arial",10)).pack(pady=(20,5))
        self.lower_alert = tk.DoubleVar(value=-18)
        tk.Scale(sliders_frame, from_=0, to=-180, orient="vertical",
                 variable=self.lower_alert, length=150, resolution=1).pack(pady=5)

    # ---------------- GPS ----------------
    def create_gps_frame(self, container):
        frame = tk.Frame(container)
        self.frames["gps"] = frame

        tk.Label(frame, text="🔹 GPS del Robot 🔹", font=("Arial", 14, "bold")).pack(pady=10)

        self.canvas_gps = Canvas(frame, width=50, height=50)
        self.canvas_gps.place(x=10, y=10)
        self.gps_led = self.canvas_gps.create_oval(5,5,45,45, fill="grey")
        self.gps_status = tk.Label(frame, text="Estado GPS", fg="red", font=("Arial",11))
        self.gps_status.place(x=70, y=20)

        control_frame = tk.Frame(frame)
        control_frame.pack(pady=5)
        tk.Label(control_frame, text="Latitud Centro").grid(row=0,column=0)
        self.lat_center_entry = tk.Entry(control_frame)
        self.lat_center_entry.grid(row=0,column=1)
        tk.Label(control_frame, text="Longitud Centro").grid(row=1,column=0)
        self.lon_center_entry = tk.Entry(control_frame)
        self.lon_center_entry.grid(row=1,column=1)
        tk.Button(control_frame, text="Predeterminado", command=self.set_default_center).grid(row=2,column=0)
        tk.Button(control_frame, text="Ingresar", command=self.set_custom_center).grid(row=2,column=1)
        tk.Label(control_frame, text="Rango del cuadrado (km)").grid(row=3,column=0,columnspan=2)
        self.range_slider = tk.Scale(control_frame, from_=0.1, to=5, resolution=0.1,
                                     orient=tk.HORIZONTAL, command=lambda x:self.update_square())
        self.range_slider.set(0.5)
        self.range_slider.grid(row=4,column=0,columnspan=2)

        map_frame = tk.Frame(frame)
        map_frame.pack(padx=10,pady=10)
        self.map_widget = tkintermapview.TkinterMapView(map_frame, width=585, height=325, corner_radius=0)
        self.map_widget.pack()
        self.map_widget.set_position(self.CENTER_LAT, self.CENTER_LON)
        self.map_widget.set_zoom(17)
        self.marker = self.map_widget.set_marker(self.CENTER_LAT, self.CENTER_LON, text="Robot")

        self.led_label = tk.Label(frame, width=10,height=2,bg="green")
        self.led_label.pack(pady=5)
        self.status_label = tk.Label(frame, text="Dentro del rango")
        self.status_label.pack()

        self.lat_center_entry.insert(0,str(self.CENTER_LAT))
        self.lon_center_entry.insert(0,str(self.CENTER_LON))
        self.update_square()

    # ---------------- ERRORES ----------------
    def create_error_frame(self, container):
        frame = tk.Frame(container)
        self.frames["errores"] = frame

        tk.Label(frame, text="🔹 Informe de errores 🔹", font=("Arial", 18, "bold")).pack(pady=15)
        
        self.error_text = tk.Text(frame, width=80, height=25, font=("Arial", 14), wrap="word", state="normal")
        self.error_text.pack(pady=10, padx=10)
        self.error_text.insert("end", "Aquí se mostrarán los errores del robot...\n")
        
        tk.Button(
            frame, 
            text="Ver explicación de errores", 
            font=("Arial", 16, "bold"),
            bg="#FFA500", fg="black",
            padx=10, pady=10,
            command=self.show_error_explanations
        ).pack(pady=15)

    def show_error_explanations(self):
        win = Toplevel(self.root)
        win.title("Explicación de errores")
        win.geometry("600x400")
        win.resizable(True, True)

        canvas = tk.Canvas(win)
        scrollbar = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for code, (desc, explain) in ERRORS_INFO.items():
            lbl_code = tk.Label(scroll_frame, text=f"{code}: {desc}", font=("Arial", 14, "bold"), anchor="w", fg="red")
            lbl_code.pack(fill="x", padx=15, pady=5)
            lbl_explain = tk.Label(scroll_frame, text=f"→ {explain}", font=("Arial", 12), anchor="w", wraplength=550)
            lbl_explain.pack(fill="x", padx=30, pady=2)

    # ---------------- VOLTAJE ----------------
    def create_voltaje_frame(self, container):
        frame = tk.Frame(container)
        self.frames["voltaje"] = frame

        tk.Label(frame, text="🔹 Voltaje del Robot 🔹", font=("Arial", 14, "bold")).pack(pady=10)

        main_frame = tk.Frame(frame)
        main_frame.pack(fill="both", expand=True, pady=10)

        # Gráfico
        graph_frame = tk.Frame(main_frame)
        graph_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        self.fig_voltaje, self.ax_voltaje = plt.subplots(figsize=(4.5,3))
        self.ax_voltaje.set_title("Voltaje (V)")
        self.ax_voltaje.set_xlabel("Tiempo (muestras)")
        self.ax_voltaje.set_ylabel("Voltaje (V)")
        self.ax_voltaje.grid(True)
        self.voltaje_line, = self.ax_voltaje.plot([], [], label="Voltaje", color="green")
        self.ax_voltaje.axhline(35, color='red', linestyle='--', label="Sobrevoltaje")
        self.ax_voltaje.axhline(20, color='orange', linestyle='--', label="Batería baja")
        self.ax_voltaje.legend(fontsize=8)
        self.fig_voltaje.tight_layout()
        self.voltaje_canvas_widget = FigureCanvasTkAgg(self.fig_voltaje, master=graph_frame)
        self.voltaje_canvas_widget.get_tk_widget().pack(fill="both", expand=True)

        # Visualización 4 cuadros
        vis_frame = tk.Frame(main_frame)
        vis_frame.pack(side="left", padx=10, pady=10)
        tk.Label(vis_frame, text="Estado de batería", font=("Arial",12,"bold")).pack(pady=5)
        self.battery_boxes = []
        for i in range(4):
            box = tk.Label(vis_frame, width=6, height=3, bg="gray", relief="raised", borderwidth=2)
            box.pack(pady=3)
            self.battery_boxes.append(box)



    # ---------------- UPDATE STATUS ----------------
    def update_status(self):
        while True:
            try:
                r=requests.get(f'{urlDB}{nombreDispositivo}.json')
                if r.status_code==200:
                    d=r.json()
                    balanceo=float(d.get('Balanceo',0))
                    lat=float(d.get('Latitud',0))
                    lon=float(d.get('Longitud',0))
                    voltaje=float(d.get('Voltaje',3.0))

                    

                    # ---------------- BALANCEO ----------------
                    self.balanceo_data.append(balanceo)
                    if self.frames["balanceo"].winfo_ismapped():
                        xdata = range(len(self.balanceo_data))
                        self.balanceo_line.set_data(xdata,self.balanceo_data)
                        self.lower_line.set_data([0,len(self.balanceo_data)-1],[self.lower_alert.get()]*2)
                        self.upper_line.set_data([0,len(self.balanceo_data)-1],[self.upper_alert.get()]*2)
                        self.ax_balanceo.relim()
                        self.ax_balanceo.autoscale_view()
                        self.balanceo_canvas_widget.draw_idle()

                        # Determinar estado balanceo
                        if balanceo >= 80:
                            alert_state = "ROJO_POS"
                            led_color = "red"
                            status_text = f"Peligro robot se cayó ({balanceo:.2f}°)"
                            status_fg = "red"
                        elif balanceo <= -80:
                            alert_state = "ROJO_NEG"
                            led_color = "red"
                            status_text = f"Peligro robot se volcó ({balanceo:.2f}°)"
                            status_fg = "red"
                        elif balanceo > self.upper_alert.get():
                            alert_state = "AMARILLO_POS"
                            led_color = "yellow"
                            status_text = f"Se va a caer ({balanceo:.2f}°)"
                            status_fg = "orange"
                        elif balanceo < self.lower_alert.get():
                            alert_state = "AMARILLO_NEG"
                            led_color = "yellow"
                            status_text = f"Se fuerzan motores ({balanceo:.2f}°)"
                            status_fg = "orange"
                        else:
                            alert_state = "VERDE"
                            led_color = "green"
                            status_text = f"Balanceo estable ({balanceo:.2f}°)"
                            status_fg = "blue"

                        self.canvas_balanceo.itemconfig(self.balanceo_led, fill=led_color)
                        self.balanceo_status.config(text=status_text, fg=status_fg)

       
                    # ---------------- GPS ----------------
                    self.lat_data.append(lat)
                    self.lon_data.append(lon)
                    if self.frames["gps"].winfo_ismapped():
                        self.update_marker_from_firebase(lat, lon)

                    # ---------------- VOLTAJE ----------------
                    self.voltaje_data.append(voltaje+1.2)
                    if self.frames["voltaje"].winfo_ismapped():
                        xdata = range(len(self.voltaje_data))
                        self.voltaje_line.set_data(xdata,self.voltaje_data)
                        self.ax_voltaje.relim()
                        self.ax_voltaje.autoscale_view()
                        self.voltaje_canvas_widget.draw_idle()



                        # Visualización batería
                        def voltage_to_level(v):
                            V_MIN = 21.2
                            V_MAX = 25.2
                            if v <= V_MIN:
                                return 1  # crítico, rojo
                            elif v >= V_MAX:
                                return 4  # lleno, verde
                            else:
                                percent = (v - V_MIN) / (V_MAX - V_MIN)
                                if percent <= 0.25:
                                    return 1  # rojo
                                elif percent <= 0.5:
                                    return 2  # naranja
                                elif percent <= 0.75:
                                    return 3  # amarillo
                                else:
                                    return 4  # verde

                        level = voltage_to_level(voltaje)

                        for i, box in enumerate(self.battery_boxes):
                            if i < level:
                                if level == 4:
                                    box.config(bg="green")
                                elif level == 3:
                                    box.config(bg="yellow")
                                elif level == 2:
                                    box.config(bg="orange")
                                else:
                                    box.config(bg="red")
                            else:
                                box.config(bg="gray")


            except Exception as e:
                if self.frames["errores"].winfo_ismapped():
                    self.error_text.insert("end", f"{time.strftime('%H:%M:%S')} - Error: {e}\n")
                    self.error_text.see("end")
            time.sleep(1)



        # ---------------- LEER ÚLTIMO REGISTRO DE SQLITE ----------------
    def leer_ultimo_registro_sqlite(self):
        try:
            DB_FILE = "C:/Users/ASUS/Desktop/interfaz tesis/base de datos/notificaciones.db3"  # <-- pon aquí tu archivo SQLite
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT Latitud, Longitud, Velocidad, Balanceo, Voltaje
                FROM notificacion
                ORDER BY ROWID DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            conn.close()
            if row:
                lat, lon, vel, bal, volt = row
                return lat, lon, vel, bal, volt
            else:
                return 0, 0, 0, 0, 0
        except Exception as e:
            if self.frames["errores"].winfo_ismapped():
                self.error_text.insert("end", f"{time.strftime('%H:%M:%S')} - Error SQLite: {e}\n")
                self.error_text.see("end")
            return 0,0,0,0,0
        


    def actualizar_label_sqlite(self):
        # 1. Validación de seguridad para Sliders
        if not hasattr(self, 'upper_alert'):
            self.root.after(100, self.actualizar_label_sqlite)
            return

        # 2. Obtener datos de SQLite y Sliders
        lat, lon, vel, bal, volt = self.leer_ultimo_registro_sqlite()
        lim_sup = self.upper_alert.get()
        lim_inf = self.lower_alert.get()
        hora = time.strftime('%H:%M:%S')

        alerta_detectada = False
        cod_error = ""
        mensaje_interfaz = ""

        # --- LÓGICA DE DETECCIÓN DE ALERTAS ---
        if bal > lim_sup:
            cod_error = "BAL-01"
            mensaje_interfaz = (f"⚠️ ALERTA: {hora}\nCÓDIGO: {cod_error}\n"
                                f"EVENTO: Inclinación Superior\nVALOR: {bal:.2f}°\n"
                                f"COORD: {lat:.4f}, {lon:.4f}")
            alerta_detectada = True
        elif bal < lim_inf:
            cod_error = "BAL-02"
            mensaje_interfaz = (f"⚠️ ALERTA: {hora}\nCÓDIGO: {cod_error}\n"
                                f"EVENTO: Inclinación Inferior\nVALOR: {bal:.2f}°\n"
                                f"COORD: {lat:.4f}, {lon:.4f}")
            alerta_detectada = True
        elif volt > 35:
            cod_error = "VOL-01"
            mensaje_interfaz = (f"⚡ ALERTA: {hora}\nCÓDIGO: {cod_error}\n"
                                f"EVENTO: SOBREVOLTAJE\nVALOR: {volt:.2f}V\n"
                                f"COORD: {lat:.4f}, {lon:.4f}")
            alerta_detectada = True
        elif volt < 20:
            cod_error = "VOL-02"
            mensaje_interfaz = (f"🪫 ALERTA: {hora}\nCÓDIGO: {cod_error}\n"
                                f"EVENTO: BATERÍA CRÍTICA\nVALOR: {volt:.2f}V\n"
                                f"COORD: {lat:.4f}, {lon:.4f}")
            alerta_detectada = True
        elif bal > 80:
            cod_error = "BAL-03"
            mensaje_interfaz = (f"🪫 ALERTA: {hora}\nCÓDIGO: {cod_error}\n"
                                f"EVENTO: ROBOT SE CAYO\nVALOR: {bal:.2f}°\n"
                                f"COORD: {lat:.4f}, {lon:.4f}")
            alerta_detectada = True

        # --- GESTIÓN DE INTERFAZ Y RESET ---
        if alerta_detectada:
            # Si hay una falla real, el botón RESET vuelve a su color gris original
            self.btn_reset.config(bg="lightgrey", fg="black")
            
            # Actualizar Label y LED a ROJO
            self.voltaje_led_label.config(text=mensaje_interfaz, fg="red", font=("Arial", 10, "bold"))
            self.voltaje_led_canvas.itemconfig(self.voltaje_led, fill="red")
            
            # GUARDAR EN EL HISTORIAL (Memoria interna)
            registro = f"[{hora}] {cod_error} | Bal: {bal:.2f}° | Volt: {volt:.2f}V | GPS: {lat}, {lon}"
            # Evitar duplicados seguidos en la lista
            if not self.historial_alertas or self.historial_alertas[-1].split('|')[0] != f"[{hora}] {cod_error} ":
                self.historial_alertas.append(registro)

        else:
            # Si NO hay alerta, solo actualizamos si el usuario NO ha presionado RESET manualmente
            # (Si el botón está en verde, respetamos el estado de "Silencio" del usuario)
            if self.btn_reset.cget("bg") != "green":
                estado_ok = (f"✅ SISTEMA ESTABLE\n"
                             f"Hora: {hora}\n"
                             f"Balanceo: {bal:.2f}°\n"
                             f"Voltaje: {volt:.2f}V\n\n"
                             f"Monitoreando SQLite...")
                self.voltaje_led_label.config(text=estado_ok, fg="green", font=("Arial", 10))
                self.voltaje_led_canvas.itemconfig(self.voltaje_led, fill="green")

        # Re-ejecutar cada 2 segundos
        self.root.after(2000, self.actualizar_label_sqlite)




    def resetear_datos(self):
        """Esta es la función para el otro botón de Resetear que pusimos antes"""
        self.balanceo_data.clear()
        self.voltaje_data.clear()
        self.positions.clear()
        messagebox.showinfo("Reset", "Los gráficos han sido limpiados.")    


    # --- ESTA FUNCIÓN DEBE EXISTIR DENTRO DE LA CLASE ---
    def guardar_en_txt(self):
        try:
            import os
            # 1. Obtener la ruta
            directorio_actual = os.path.dirname(os.path.abspath(__file__))
            ruta_final = os.path.join(directorio_actual, "datos_robot_registrados.txt")
            
            # 2. Verificar si hay algo que guardar
            if not self.historial_alertas:
                messagebox.showinfo("Información", "No hay errores nuevos para guardar.")
                return

            # 3. Escribir el historial acumulado
            with open(ruta_final, "a", encoding="utf-8") as f:
                f.write(f"\n--- REPORTE: {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                for error in self.historial_alertas:
                    f.write(error + "\n")
                f.write("-" * 50 + "\n")
            
            # 4. Limpiar historial tras guardar
            self.historial_alertas.clear()
            messagebox.showinfo("Éxito", f"Historial guardado en:\n{ruta_final}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")

    # --- TAMBIÉN AGREGA LA FUNCIÓN RESET SI NO LA TIENES ---
    def reset_alerta_manual(self):
        hora_reset = time.strftime('%H:%M:%S')
        
        # Activar modo RESET temporal
        self.reset_temporal = True
        
        # LED y Label en verde mientras dura el RESET
        self.voltaje_led_canvas.itemconfig(self.voltaje_led, fill="green")
        self.voltaje_led_label.config(
            text=f"✅ SISTEMA RESETEADO\nHora: {hora_reset}\nEsperando nuevo dato...",
            fg="green",
            font=("Arial", 10)
        )
        
        # Botón en verde
        self.btn_reset.config(bg="green", fg="white")
        
        # Desactivar modo RESET temporal después de 15 segundos
        def terminar_reset():
            self.reset_temporal = False
            # Botón vuelve a gris
            self.btn_reset.config(bg="lightgrey", fg="black")
            # Forzar actualización inmediata del label
            self.actualizar_label_sqlite()
        
        self.root.after(15000, terminar_reset)




    # ---------------- GPS Y CENTRO ----------------
    def update_square(self):
        range_km = self.range_slider.get()
        half_deg = (range_km*self.DEG_PER_KM)/2
        lat_min = self.CENTER_LAT-half_deg
        lat_max = self.CENTER_LAT+half_deg
        lon_min = self.CENTER_LON-half_deg
        lon_max = self.CENTER_LON+half_deg
        if self.square_path:
            self.map_widget.delete(self.square_path)
        self.square_path = self.map_widget.set_path(
            [(lat_min,lon_min),(lat_min,lon_max),(lat_max,lon_max),(lat_max,lon_min),(lat_min,lon_min)],
            color="blue", width=4
        )
        self.map_widget.set_position(self.CENTER_LAT,self.CENTER_LON)
        self.map_widget.set_zoom(self.calculate_zoom(range_km))

    def calculate_zoom(self, range_km):
        if range_km <= 0.2: return 18
        elif range_km <=0.5: return 17
        elif range_km <=1: return 16
        elif range_km <=2: return 15
        elif range_km <=3: return 14
        else: return 13

    def set_default_center(self):
        self.CENTER_LAT = 0.35852
        self.CENTER_LON = -78.1111
        self.lat_center_entry.delete(0, tk.END)
        self.lat_center_entry.insert(0,str(self.CENTER_LAT))
        self.lon_center_entry.delete(0, tk.END)
        self.lon_center_entry.insert(0,str(self.CENTER_LON))
        self.update_square()

    def set_custom_center(self):
        try:
            lat = float(self.lat_center_entry.get())
            lon = float(self.lon_center_entry.get())
            self.CENTER_LAT = lat
            self.CENTER_LON = lon
            self.update_square()
        except:
            pass

    def update_marker_from_firebase(self, lat, lon):
        if not self.frames["gps"].winfo_ismapped():
            return

        # Verificar si el GPS está activo
        if lat == 0 and lon == 0:
            self.canvas_gps.itemconfig(self.gps_led, fill="red")
            self.gps_status.config(text="GPS OFF", fg="red")
            return

        # GPS OK
        self.canvas_gps.itemconfig(self.gps_led, fill="green")
        self.gps_status.config(text="GPS OK", fg="blue")
        self.marker.set_position(lat, lon)
        self.positions.append((lat, lon))

        # Eliminar trayectoria anterior si existe
        if self.trajectory_path:
            self.map_widget.delete(self.trajectory_path)
        self.trajectory_path = self.map_widget.set_path(self.positions, color="red", width=3)

        # Calcular límites del cuadrado
        range_km = self.range_slider.get()
        half_deg = (range_km * self.DEG_PER_KM) / 2
        lat_min = self.CENTER_LAT - half_deg
        lat_max = self.CENTER_LAT + half_deg
        lon_min = self.CENTER_LON - half_deg
        lon_max = self.CENTER_LON + half_deg

        # Verificar si está dentro o fuera del rango
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            # Dentro del rango → LED verde
            self.led_label.config(bg="green")
            self.status_label.config(text="Dentro del rango")
        else:
            # Fuera del rango → LED rojo, igual que el LED de voltaje
            self.led_label.config(bg="red")
            self.status_label.config(text="⚠️ FUERA DEL RANGO")

            # Sincronizar alerta con LED de voltaje
            self.voltaje_led_canvas.itemconfig(self.voltaje_led, fill="red")
            self.voltaje_led_label.config(
                text=f"⚠️ ALERTA: Robot fuera de rango\nLat: {lat:.4f}, Lon: {lon:.4f}",
                fg="red",
                font=("Arial", 10, "bold")
            )
            # Opcional: agregar al historial de alertas
            hora = time.strftime('%H:%M:%S')
            registro = f"[{hora}] GPS fuera de rango | Lat: {lat:.4f}, Lon: {lon:.4f}"
            if not self.historial_alertas or self.historial_alertas[-1] != registro:
                self.historial_alertas.append(registro)



if __name__=="__main__":
    root=tk.Tk()
    app=RobotStatusApp(root)
    root.mainloop()