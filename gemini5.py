import google.generativeai as genai
import PIL.Image
import os
import cv2
import numpy as np
import requests
import time
from gpiozero import AngularServo
from time import sleep
import sys

# Configurar API key de Google AI Studio
genai.configure(api_key="AIzaSyCQIevCGurB0NtFerXdlS5sbunj_ajCT8c")  # Reemplaza con tu API key real

# Configurar servo con rango de 0° a 180°
servo = AngularServo(18, min_angle=0, max_angle=180)

def mover_servo():
    servo.angle = 0
    print(f"➤ Moviendo a 0°", file=sys.stderr)
    sleep(1)
    servo.angle = 120
    print(f"➤ Moviendo a 80°", file=sys.stderr)
    sleep(0.2)
    servo.angle = 0
    print(f"➤ Moviendo a 0°", file=sys.stderr)

def analizar_imagen_gemini(image_path):
    # Usar el modelo correcto
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    # Abrir la imagen con PIL
    img = PIL.Image.open(image_path)
    
    prompt = """Analiza esta imagen de medición de presión arterial y extrae SOLAMENTE los tres valores numéricos en este orden:
    1. Presión sistólica
    2. Presión diastólica  
    3. Frecuencia cardíaca (BPM)

    FORMATO DE RESPUESTA REQUERIDO:
    valor1,valor2,valor3

    REGLAS:
    - Solo números separados por comas
    - Sin texto adicional, unidades, explicaciones o símbolos
    - Si no puedes identificar un valor, usa "?" en su lugar
    - Ejemplo: 120,80,65"""
    
    try:
        response = model.generate_content([
            prompt,
            img
        ])
        
        # Limpiar la respuesta
        resultado = response.text.strip()
        print("Valores obtenidos:", resultado, file=sys.stderr)
        return resultado
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None

def procesar_imagen():
    # URL de la foto instantánea
    url = "http://10.214.59.73:8080/photo.jpg"

    # Descargar la imagen
    r = requests.get(url)
    if r.status_code == 200:
        with open("captura_cel.jpg", "wb") as f:
            f.write(r.content)
        print("Foto guardada como captura_cel.jpg", file=sys.stderr)
    else:
        print("Error al obtener la foto", file=sys.stderr)
        return None

    # === Procesamiento ===
    img = cv2.imread("captura_cel.jpg")

    # Girar la imagen 90 grados
    img_rotada = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    cv2.imwrite("captura_rotada_90.jpg", img_rotada)
    print("Imagen girada 90 grados y guardada como captura_rotada_90.jpg", file=sys.stderr)

    # === Binarización TRUNC ===
    print("Aplicando binarización TRUNC...", file=sys.stderr)

    # Convertir a escala de grises
    gris = cv2.cvtColor(img_rotada, cv2.COLOR_BGR2GRAY)
    cv2.imwrite("captura_gris.jpg", gris)
    print("Imagen en escala de grises guardada como captura_gris.jpg", file=sys.stderr)

    # Umbral para TRUNC
    umbral = 127

    # Aplicar THRESH_TRUNC
    _, binaria_trunc = cv2.threshold(gris, umbral, 255, cv2.THRESH_TRUNC)
    cv2.imwrite("captura_trunc.jpg", binaria_trunc)
    print("THRESH_TRUNC guardada como captura_trunc.jpg", file=sys.stderr)

    print("Proceso de imagen completado", file=sys.stderr)
    return "captura_trunc.jpg"

def main():
    # Activar servo al inicio
    print("=== ACTIVANDO SERVO AL INICIO ===", file=sys.stderr)
    mover_servo()
    
    # Esperar 50 segundos
    print("Esperando 50 segundos antes de capturar la imagen...", file=sys.stderr)
    time.sleep(50)
    
    # Procesar la imagen
    imagen_procesada = procesar_imagen()
    
    resultado_final = None
    
    if imagen_procesada:
        # Analizar la imagen con Gemini
        resultado = analizar_imagen_gemini(imagen_procesada)
        if resultado:
            # Procesar el resultado para el formato esperado
            partes = resultado.split(',')
            if len(partes) == 3:
                sistolica = partes[0]
                diastolica = partes[1]
                bpm = partes[2]
                
                # Imprimir en el formato que el método run espera
                print(f"Presión: {sistolica}/{diastolica}")
                print(f"BPM: {bpm}")
                
                resultado_final = f"{sistolica}/{diastolica}|{bpm}"
            else:
                print("Error: Formato de resultado incorrecto", file=sys.stderr)
        else:
            print("No se pudo analizar la imagen", file=sys.stderr)
    else:
        print("No se pudo procesar la imagen correctamente", file=sys.stderr)
    
    # Activar servo al final
    print("=== ACTIVANDO SERVO AL FINAL ===", file=sys.stderr)
    mover_servo()
    
    return resultado_final

# Programa principal
if __name__ == "__main__":
    resultado = main()
    if resultado:
        # También imprimir el resultado final en stderr para depuración
        print(f"Resultado final: {resultado}", file=sys.stderr)
