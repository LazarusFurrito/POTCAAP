from heartrate_monitor import HeartRateMonitor
import time
import argparse
import numpy as np

# Configuración de promedios
MUESTRAS_SPO2 = 15
MUESTRAS_BPM = 8

class SpO2Monitor:
    def __init__(self, num_muestras=15):
        self.num_muestras = num_muestras
        self.muestras_spo2 = []
        self.ultimo_spo2 = None
    
    def procesar_spo2(self, spo2_value):
        # ... (código de la clase SpO2Monitor que ya teníamos)

class BPMMonitor:
    def __init__(self, num_muestras=8):
        # ... (código de la clase BPMMonitor que ya teníamos)

class HeartRateMonitorEstable(HeartRateMonitor):
    def __init__(self, print_raw=False, print_result=False):
        # ... (código de la clase HeartRateMonitorEstable que ya teníamos)

    def run_sensor(self):
        # ... (código del método run_sensor que ya teníamos)
    
    def get_spo2(self):
        return self.spo2_value
    
    def get_bpm(self):
        return self.bpm_value

# === AQUÍ METES LA NUEVA FUNCIÓN ===
def obtener_spo2(duracion=30):
    """
    Función que solo retorna el valor de SpO2
    """
    print('Obteniendo medición de SpO2...')
    
    hrm = HeartRateMonitorEstable(print_raw=False, print_result=True)
    hrm.start_sensor()
    
    valores_spo2 = []
    tiempo_inicio = time.time()
    
    try:
        while time.time() - tiempo_inicio < duracion:
            spo2_actual = hrm.get_spo2()
            
            if spo2_actual is not None:
                valores_spo2.append(spo2_actual)
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print('Medición interrumpida')
    
    hrm.stop_sensor()
    
    # Calcular y retornar SpO2
    if valores_spo2:
        promedio = sum(valores_spo2) / len(valores_spo2)
        spo2_final = round(promedio, 1)
        print(f"SpO2 obtenido: {spo2_final}%")
        return spo2_final
    else:
        print("No se pudo obtener SpO2")
        return None

# === CÓDIGO PRINCIPAL ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor estable de BPM y SpO2 con MAX30102")
    parser.add_argument("-t", "--time", type=int, default=30,
                        help="duración en segundos para leer del sensor, por defecto 30")
    args = parser.parse_args()

    # === USO DE LA NUEVA FUNCIÓN ===
    spo2 = obtener_spo2(args.time)
    
    if spo2:
        print(f"El valor de oxígeno en sangre es: {spo2}%")
    else:
        print("No se pudo obtener una lectura válida de SpO2")