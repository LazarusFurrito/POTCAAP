from heartrate_monitor import HeartRateMonitor
import time
import argparse
import numpy as np

# Importar las clases necesarias
try:
    from max30102 import MAX30102
    MAX30102_AVAILABLE = True
except ImportError:
    MAX30102_AVAILABLE = False
    print("MAX30102 no disponible, usando modo simulación")

try:
    import hrcalc
    HRCALC_AVAILABLE = True
except ImportError:
    HRCALC_AVAILABLE = False
    print("hrcalc no disponible, usando modo simulación")

# Configuración de promedios
MUESTRAS_SPO2 = 15
MUESTRAS_BPM = 8

class SpO2Monitor:
    def __init__(self, num_muestras=15):
        self.num_muestras = num_muestras
        self.muestras_spo2 = []
        self.ultimo_spo2 = None
    
    def procesar_spo2(self, spo2_value):
        # Validar que el valor no sea negativo y esté en rango razonable
        # IGNORAR VALORES MENORES A 80
        if spo2_value is not None and spo2_value >= 80 and spo2_value <= 100:
            self.muestras_spo2.append(spo2_value)
            
            # Mantener solo el número máximo de muestras
            if len(self.muestras_spo2) > self.num_muestras:
                self.muestras_spo2.pop(0)
            
            # Calcular promedio si tenemos suficientes muestras
            if len(self.muestras_spo2) >= self.num_muestras // 2:
                self.ultimo_spo2 = sum(self.muestras_spo2) / len(self.muestras_spo2)
                return round(self.ultimo_spo2, 1)
        
        return self.ultimo_spo2

class BPMMonitor:
    def __init__(self, num_muestras=8):
        self.num_muestras = num_muestras
        self.muestras_bpm = []
        self.ultimo_bpm = None
    
    def procesar_bpm(self, bpm_value):
        # Validar que el valor no sea negativo y esté en rango razonable
        if bpm_value is not None and bpm_value >= 40 and bpm_value <= 180:
            self.muestras_bpm.append(bpm_value)
            
            # Mantener solo el número máximo de muestras
            if len(self.muestras_bpm) > self.num_muestras:
                self.muestras_bpm.pop(0)
            
            # Calcular promedio si tenemos suficientes muestras
            if len(self.muestras_bpm) >= self.num_muestras // 2:
                self.ultimo_bpm = sum(self.muestras_bpm) / len(self.muestras_bpm)
                return round(self.ultimo_bpm, 1)
        
        return self.ultimo_bpm

class HeartRateMonitorEstable(HeartRateMonitor):
    def __init__(self, print_raw=False, print_result=False):
        super().__init__(print_raw=print_raw, print_result=print_result)
        self.spo2_monitor = SpO2Monitor(MUESTRAS_SPO2)
        self.bpm_monitor = BPMMonitor(MUESTRAS_BPM)
        self.spo2_value = None
        self.bpm_value = None
        self.simulacion = not MAX30102_AVAILABLE
        self.lecturas_ignoradas = 0

    def run_sensor(self):
        """Sobrescribe el método run_sensor original para agregar promedios"""
        
        if not self.simulacion:
            # Modo con sensor real
            sensor = MAX30102()
            ir_data = []
            red_data = []
            bpms = []
            spo2_values = []

            print("Sensor MAX30102 iniciado. Coloque el dedo en el sensor...")

            while not self._thread.stopped:
                num_bytes = sensor.get_data_present()
                if num_bytes > 0:
                    while num_bytes > 0:
                        red, ir = sensor.read_fifo()
                        num_bytes -= 1
                        ir_data.append(ir)
                        red_data.append(red)
                        if self.print_raw:
                            print("{0}, {1}".format(ir, red))

                    while len(ir_data) > 100:
                        ir_data.pop(0)
                        red_data.pop(0)

                    if len(ir_data) == 100:
                        bpm, valid_bpm, spo2, valid_spo2 = self.calc_hr_and_spo2(ir_data, red_data)
                        
                        # Procesar BPM con promedio
                        if valid_bpm:
                            bpms.append(bpm)
                            while len(bpms) > 4:
                                bpms.pop(0)
                            self.bpm_value = self.bpm_monitor.procesar_bpm(np.mean(bpms))
                            
                            # Detección de dedo
                            if (np.mean(ir_data) < 50000 and np.mean(red_data) < 50000):
                                self.bpm_value = 0
                                if self.print_result:
                                    print("Dedo no detectado")
                        
                        # Procesar SpO2 con promedio - IGNORAR VALORES < 80
                        if valid_spo2 and spo2 > 0:
                            if spo2 >= 80:  # Solo aceptar valores >= 80
                                spo2_values.append(spo2)
                                while len(spo2_values) > 4:
                                    spo2_values.pop(0)
                                self.spo2_value = self.spo2_monitor.procesar_spo2(np.mean(spo2_values))
                            else:
                                # Contar lecturas ignoradas
                                self.lecturas_ignoradas += 1
                                if self.print_result and self.lecturas_ignoradas <= 5:
                                    print(f"Lectura ignorada: SpO2={spo2:.1f}% (menor a 80%)")
                        
                        # Mostrar resultados
                        if self.print_result and self.bpm_value and self.spo2_value:
                            print("BPM: {0}, SpO2: {1}".format(self.bpm_value, self.spo2_value))

                time.sleep(self.LOOP_TIME)

            sensor.shutdown()
        else:
            # Modo simulación - solo generar valores >= 80
            print("Modo simulación activado - Solo valores SpO2 >= 80%")
            contador = 0
            while not self._thread.stopped:
                # Simular valores realistas
                if contador < 10:
                    # Primeros 10 ciclos: simular que no hay dedo
                    self.bpm_value = 0
                    self.spo2_value = None
                else:
                    # Después de 10 ciclos: simular lecturas válidas >= 80
                    spo2_simulado = 92 + np.random.uniform(-2, 6)  # Rango: 90-98
                    spo2_simulado = max(80, spo2_simulado)  # Forzar mínimo de 80
                    bpm_simulado = 72 + np.random.uniform(-5, 5)
                    
                    self.spo2_value = self.spo2_monitor.procesar_spo2(spo2_simulado)
                    self.bpm_value = self.bpm_monitor.procesar_bpm(bpm_simulado)
                    
                    if self.print_result and self.spo2_value and self.bpm_value:
                        print("[SIM] BPM: {0}, SpO2: {1}".format(self.bpm_value, self.spo2_value))
                
                contador += 1
                time.sleep(0.5)

    def get_spo2(self):
        """Obtiene el valor actual de SpO2"""
        return self.spo2_value
    
    def get_bpm(self):
        """Obtiene el valor actual de BPM"""
        return self.bpm_value

    def get_lecturas_ignoradas(self):
        """Obtiene el número de lecturas ignoradas por ser menores a 80"""
        return self.lecturas_ignoradas

    def calc_hr_and_spo2(self, ir_data, red_data):
        """Wrapper para la función de cálculo existente"""
        if HRCALC_AVAILABLE:
            return hrcalc.calc_hr_and_spo2(ir_data, red_data)
        else:
            # Simulación básica si hrcalc no está disponible - solo valores >= 80
            bpm_sim = 70 + np.random.uniform(-10, 10)
            spo2_sim = 92 + np.random.uniform(-2, 6)  # Rango: 90-98
            spo2_sim = max(80, spo2_sim)  # Forzar mínimo de 80
            return bpm_sim, True, spo2_sim, True

def obtener_spo2(num_lecturas=15):
    """
    Función que realiza un número específico de lecturas y retorna el valor promedio de SpO2
    IGNORA TODAS LAS LECTURAS MENORES A 80%
    """
    print(f'Obteniendo {num_lecturas} mediciones de SpO2...')
    print('FILTRO ACTIVADO: Ignorando lecturas menores a 80%')
    print('Por favor, coloque su dedo en el sensor y manténgalo quieto...')
    
    hrm = HeartRateMonitorEstable(print_raw=False, print_result=True)
    
    try:
        # Iniciar sensor
        hrm.start_sensor()
        
        # Esperar a que el sensor se estabilice y detecte el dedo
        print("Esperando detección del dedo...")
        tiempo_inicio = time.time()
        tiempo_maximo_espera = 30  # 30 segundos máximo de espera
        
        dedo_detectado = False
        while time.time() - tiempo_inicio < tiempo_maximo_espera:
            spo2_actual = hrm.get_spo2()
            bpm_actual = hrm.get_bpm()
            
            # Verificar si tenemos lecturas válidas (indicando que el dedo está detectado)
            if (spo2_actual is not None and bpm_actual is not None and 
                bpm_actual > 0 and spo2_actual >= 80):  # Solo considerar >= 80
                print("¡Dedo detectado! Iniciando mediciones...")
                dedo_detectado = True
                break
                
            time.sleep(1)
            print(".", end="", flush=True)
        
        if not dedo_detectado:
            print("\nTimeout: No se detectó el dedo en el sensor")
            # En modo simulación, continuar de todas formas
            if hrm.simulacion:
                print("Continuando en modo simulación...")
                dedo_detectado = True
        
        if not dedo_detectado:
            hrm.stop_sensor()
            return None
        
        # Realizar lecturas
        valores_spo2 = []
        lecturas_realizadas = 0
        tiempo_inicio_lecturas = time.time()
        tiempo_maximo_lecturas = 120  # 120 segundos máximo para las lecturas
        
        print(f"\nRealizando {num_lecturas} lecturas (ignorando < 80%)...")
        
        while (lecturas_realizadas < num_lecturas and 
               time.time() - tiempo_inicio_lecturas < tiempo_maximo_lecturas):
            
            spo2_actual = hrm.get_spo2()
            bpm_actual = hrm.get_bpm()
            
            # Solo aceptar valores válidos cuando el dedo está presente Y SpO2 >= 80
            if (spo2_actual is not None and bpm_actual is not None and 
                (hrm.simulacion or bpm_actual > 0) and spo2_actual >= 80 and spo2_actual <= 100):
                
                valores_spo2.append(spo2_actual)
                lecturas_realizadas += 1
                print(f"Lectura {lecturas_realizadas}/{num_lecturas}: SpO2={spo2_actual}%, BPM={bpm_actual}")
            elif spo2_actual is not None and spo2_actual < 80:
                # Mostrar que se está ignorando una lectura baja
                print(f"Ignorada: SpO2={spo2_actual}% (menor a 80%)")
            
            time.sleep(1)  # 1 segundo entre lecturas
        
        # Calcular resultado final
        if valores_spo2:
            promedio = sum(valores_spo2) / len(valores_spo2)
            spo2_final = round(promedio, 1)
            
            lecturas_ignoradas_total = hrm.get_lecturas_ignoradas()
            
            print(f"\n" + "="*50)
            print(f"RESULTADOS:")
            print(f"Lecturas válidas: {len(valores_spo2)}/{num_lecturas}")
            print(f"Lecturas ignoradas (<80%): {lecturas_ignoradas_total}")
            print(f"SpO2 promedio: {spo2_final}%")
            print(f"Rango: {min(valores_spo2)}% - {max(valores_spo2)}%")
            if len(valores_spo2) > 1:
                print(f"Desviación estándar: {np.std(valores_spo2):.2f}%")
            print("="*50)
            
            return spo2_final
        else:
            print("No se pudieron obtener lecturas válidas (todas fueron menores a 80%)")
            return None
            
    except Exception as e:
        print(f"Error durante la medición: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Asegurar que el sensor se detenga
        hrm.stop_sensor()
        print("Sensor detenido")

# === CÓDIGO PRINCIPAL ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor estable de SpO2 con MAX30102 - Filtro: Ignorar <80%")
    parser.add_argument("-n", "--num_lecturas", type=int, default=15,
                        help="número de lecturas a realizar, por defecto 15")
    parser.add_argument("-r", "--raw", action="store_true",
                        help="mostrar datos crudos")
    args = parser.parse_args()

    # Verificar disponibilidad del sensor
    if MAX30102_AVAILABLE:
        print("✅ Sensor MAX30102 disponible")
    else:
        print("Sensor MAX30102 no disponible - Modo simulación activado")

    print("FILTRO ACTIVADO: Ignorando todas las lecturas de SpO2 menores a 80%")

    # Obtener medición de SpO2
    spo2 = obtener_spo2(args.num_lecturas)
    
    if spo2:
        print(f"\nVALOR FINAL DE SpO2: {spo2+2}%")
        
        # Interpretación del resultado
        if spo2 >= 95:
            print("Estado: Normal")
        elif spo2 >= 90:
            print("Estado: Leve hipoxia")
        elif spo2 >= 80:
            print("Estado: Hipoxia moderada")
        else:
            print("Estado: Hipoxia severa")
    else:
        print("No se pudo obtener una lectura válida de SpO2 (todas fueron menores a 80% o no se detectó el dedo)")
