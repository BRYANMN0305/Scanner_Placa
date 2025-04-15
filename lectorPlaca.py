import cv2
import pytesseract
import re
import tkinter as tk
from tkinter import Label, Button, Frame
from PIL import Image, ImageTk
import threading
import requests
import subprocess
import time 

# Configurar Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# URL de la API
API_URL = "https://api-lectores-cci.onrender.com/validar_placa/"

# Tiempo mínimo entre escaneos en segundos
TIEMPO_ESPERA = 7

class DetectorPlacas:
    def __init__(self, root, max_lecturas=200):
        self.root = root
        self.root.title("Detector de Placas")
        self.root.geometry("900x660")

        self.max_lecturas = max_lecturas
        self.ultima_placa = ""
        self.ultimo_tiempo = 0  # Último tiempo de escaneo

        self.frame_botones = Frame(self.root)
        self.frame_botones.pack(pady=10)

        self.label_video = Label(self.root)
        self.label_video.pack()

        self.label_placa = Label(self.root, text="Placa detectada:", font=("Arial", 14))
        self.label_placa.pack()

        self.text_placa = Label(self.root, text="Esperando...", font=("Arial", 16, "bold"), fg="green")
        self.text_placa.pack()

        self.label_puesto = Label(self.root, text="Puesto asignado: -", font=("Arial", 14))
        self.label_puesto.pack()

        # Botón para regresar a la ventana principal
        self.boton_volver = Button(self.root, text="Regresar", font=("Arial", 14), command=self.volver_main)
        self.boton_volver.pack(pady=10)

        #Indice de la camara
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.ejecutando = True
        threading.Thread(target=self.actualizar_video, daemon=True).start()

    def volver_main(self):
        """Libera la cámara y cierra la ventana, regresando a la ventana principal."""
        self.cap.release()  # Liberar la cámara
        self.root.destroy()  # Cerrar la ventana
        subprocess.Popen(["python", "main.py"])  # Abrir la ventana principal

    def es_placa_valida(self, texto):
        texto = texto.upper().strip()
        texto = re.sub(r'[^A-Z0-9-]', '', texto)
        if 6 <= len(texto) <= 8 and re.match(r'^[A-Z0-9-]+$', texto):
            return texto
        return None

    def detectar_placa(self, frame):
        alto, ancho, _ = frame.shape
        Ejex1, Ejex2 = int(ancho * 0.2), int(ancho * 0.8)
        Ejey1, Ejey2 = int(alto * 0.25), int(alto * 0.75)

        cv2.rectangle(frame, (Ejex1, Ejey1), (Ejex2, Ejey2), (0, 255, 0), 3)
        recortar = frame[Ejey1:Ejey2, Ejex1:Ejex2]
        gris = cv2.cvtColor(recortar, cv2.COLOR_BGR2GRAY)
        texto = pytesseract.image_to_string(gris, config="--psm 7 --oem 3").strip()
        return self.es_placa_valida(texto)

    def actualizar_video(self):
        while self.ejecutando:
            ret, frame = self.cap.read()
            if not ret:
                break

            nueva_placa = self.detectar_placa(frame)
            tiempo_actual = time.time()

            if nueva_placa and nueva_placa != self.ultima_placa and (tiempo_actual - self.ultimo_tiempo) >= TIEMPO_ESPERA:
                self.ultima_placa = nueva_placa
                self.ultimo_tiempo = tiempo_actual  # Actualizar tiempo del último escaneo
                self.text_placa.config(text=nueva_placa, fg="green")
                self.consultar_api(nueva_placa)
            elif not nueva_placa:
                self.text_placa.config(text="No detecta", fg="red")
                self.label_puesto.config(text="Puesto asignado: -", fg="black")
                self.ultima_placa = ""

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img = ImageTk.PhotoImage(img)
            self.label_video.config(image=img)
            self.label_video.image = img

        self.cap.release()
        self.label_video.config(image="")

    def consultar_api(self, placa):
        """ Envía la placa a la API para validación y muestra el resultado. """
        try:
            placa = placa.replace("-", "")  #Ignorar el carácter "-"
            respuesta = requests.post(API_URL, json={"placa": placa})

            if respuesta.status_code == 200:
                datos = respuesta.json()
                mensaje = datos["mensaje"]
                permitido = datos["permitido"]
                salida = datos.get("salida", False)
                puesto = datos.get("puesto", "-")

                if permitido:
                    if salida:
                        self.label_puesto.config(text="Salida confirmada", fg="blue")
                    else:
                        self.label_puesto.config(text=f"Puesto asignado: {puesto}", fg="green")
                else:
                    self.label_puesto.config(text=f"{mensaje}", fg="red")
            else:
                self.label_puesto.config(text="Error en la API", fg="red")
        except requests.exceptions.RequestException:
            self.label_puesto.config(text="No se pudo conectar con la API", fg="red")

if __name__ == "__main__":
    root = tk.Tk()
    app = DetectorPlacas(root, max_lecturas=200)
    root.mainloop()
