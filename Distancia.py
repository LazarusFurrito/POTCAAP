from gpiozero import DistanceSensor
import time
import statistics

class MedidorEstaturaPi5:
    def __init__(self, trig_pin=23, echo_pin=24, referencia_cm=210):
        self.TRIG = trig_pin
        self.ECHO = echo_pin
        self.REFERENCIA_CM = referencia_cm
        self.ALTURA_SENSOR = 210
        
        print("Inicializando medidor para Raspberry Pi 5...")
        
        self.sensor = DistanceSensor(
            echo=echo_pin,
            trigger=trig_pin,
            max_distance=2.0,
            threshold_distance=0.03,
            queue_len=3
        )
        
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)
        
        print("Sensor HC-SR04 inicializado")
        print("Iniciando calibracion...")
        
        self.factor_calibracion = self.calibrar_sensor()

    def medir_distancia_robusta(self, intentos=5):
        for intento in range(intentos):
            try:
                distancia_metros = self.sensor.distance
                distancia_cm = distancia_metros * 100
                
                if distancia_cm < 2 or distancia_cm > 200:
                    continue
                    
                return distancia_cm
                
            except Exception as e:
                if intento == intentos - 1:
                    print(f"Intento {intento+1}: Error - {e}")
                time.sleep(0.1)
        
        return None

    def calibrar_sensor(self):
        print("\n" + "="*50)
        print("CALIBRACION DEL SENSOR")
        print("="*50)
        print("Pasos para calibracion:")
        print("1. Sensor a 210 cm de altura")
        print("2. Parate a 210 cm del sensor")
        print("3. Postura recta y quieta")
        print("4. Buen ambiente (luz, poco ruido)")
        
        input("\nPresiona Enter cuando estes en posicion...")
        
        print("\nRealizando mediciones...")
        
        distancias_validas = []
        total_intentos = 15
        
        for i in range(total_intentos):
            distancia = self.medir_distancia_robusta()
            if distancia is not None:
                distancias_validas.append(distancia)
                print(f"Medida {len(distancias_validas)}: {distancia:.1f} cm")
            else:
                print(f"Medida fallida")
            
            time.sleep(0.2)
        
        if len(distancias_validas) < 8:
            print(f"Advertencia: Solo {len(distancias_validas)}/{total_intentos} mediciones validas")
            print("Consejos:")
            print("- Verifica conexiones de cables")
            print("- Asegura 5V estable para el sensor")
            print("- Ambiente mas silencioso")
            print("- Objetos en rango 2-200 cm")
            
            if len(distancias_validas) == 0:
                print("Calibracion fallida. Usando factor 1.0")
                return 1.0
        
        distancia_promedio = statistics.median(distancias_validas)
        factor = self.REFERENCIA_CM / distancia_promedio
        
        print(f"\nRESULTADOS CALIBRACION:")
        print(f"Distancia medida: {distancia_promedio:.1f} cm")
        print(f"Factor de calibracion: {factor:.3f}")
        print(f"Mediciones validas: {len(distancias_validas)}/{total_intentos}")
        
        return factor

    def medir_estatura(self, mediciones=7):
        print(f"\nRealizando {mediciones} mediciones...")
        
        distancias = []
        for i in range(mediciones):
            distancia = self.medir_distancia_robusta()
            if distancia:
                distancia_calibrada = 200-distancia * self.factor_calibracion
                distancias.append(distancia_calibrada)
                print(f"Medida {i+1}: {distancia_calibrada:.1f} cm")
            else:
                print(f"Medida {i+1}: Fallida")
            time.sleep(0.15)
        
        if len(distancias) < 3:
            print("Muy pocas mediciones validas")
            return None
        
        distancia_final = statistics.median(distancias)
        estatura = self.ALTURA_SENSOR - distancia_final
        
        if 100 <= estatura <= 220:
            return estatura
        else:
            print(f"Estatura fuera de rango: {estatura:.1f} cm")
            return None

    def menu_principal(self):
        try:
            while True:
                print("\n" + "="*40)
                print("MEDIDOR DE ESTATURA")
                print("="*40)
                print("1. Medir estatura")
                print("2. Recalibrar")
                print("3. Probar sensor")
                print("4. Salir")
                
                opcion = input("\nSelecciona opcion (1-4): ")
                
                if opcion == "1":
                    print("\nPreparando medicion...")
                    estatura = self.medir_estatura()
                    if estatura:
                        print(f"\nESTATURA: {estatura:.1f} cm")
                    else:
                        print("Error en medicion")
                        
                elif opcion == "2":
                    self.factor_calibracion = self.calibrar_sensor()
                    
                elif opcion == "3":
                    self.probar_sensor()
                    
                elif opcion == "4":
                    break
                else:
                    print("Opcion no valida")
                    
        except KeyboardInterrupt:
            print("\nPrograma terminado")
        
        finally:
            self.sensor.close()
            print("Sensor liberado")

    def probar_sensor(self):
        print("\nPRUEBA DEL SENSOR - Mueve tu mano frente al sensor")
        print("Presiona Ctrl+C para terminar")
        
        try:
            while True:
                distancia = self.medir_distancia_robusta()
                if distancia:
                    print(f"Distancia: {distancia:.1f} cm")
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("Prueba terminada")

if __name__ == "__main__":
    medidor = MedidorEstaturaPi5(referencia_cm=210)
    medidor.menu_principal()