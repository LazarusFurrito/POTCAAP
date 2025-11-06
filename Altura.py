import lgpio
import time
import statistics
import numpy as np

def leer_distancia_promedio():
    """
    Version mejorada con filtrado avanzado y tecnicas de precision
    """
    # Configuracion de pines
    TRIG_PIN = 23
    ECHO_PIN = 24
    
    # Parametros configurables
    NUM_LECTURAS = 200  # Mas muestras para mejor estadistica
    TIEMPO_TOTAL = 10   # Segundos para completar lecturas
    
    try:
        # Inicializar GPIO
        h = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(h, TRIG_PIN)
        lgpio.gpio_claim_input(h, ECHO_PIN)
        
        print(f"Realizando {NUM_LECTURAS} lecturas de distancia en {TIEMPO_TOTAL} segundos...")
        
        lecturas_cm = []
        inicio = time.time()
        lecturas_invalidas = 0
        
        # Velocidad del sonido estandar (34300 cm/s)
        velocidad_sonido = 34300
        
        for i in range(NUM_LECTURAS):
            try:
                # Limpieza robusta del trigger
                lgpio.gpio_write(h, TRIG_PIN, 0)
                time.sleep(0.0001)  # 100μs de estabilizacion
                
                # Pulso de trigger optimizado
                lgpio.gpio_write(h, TRIG_PIN, 1)
                time.sleep(0.000012)  # 12μs - tiempo optimo
                lgpio.gpio_write(h, TRIG_PIN, 0)
                
                # Pequena pausa antes de medicion
                time.sleep(0.00001)
                
                # Timeouts precisos
                timeout_inicio = 0.005  # 5ms para inicio
                timeout_fin = 0.025     # 25ms maximo (~4.3m)
                
                # Esperar inicio del eco con alta precision
                inicio_timeout = time.time()
                while lgpio.gpio_read(h, ECHO_PIN) == 0:
                    if time.time() - inicio_timeout > timeout_inicio:
                        raise Exception("Timeout inicio eco")
                    time.sleep(0.0000002)  # 0.2μs - mayor precision
                
                inicio_eco = time.perf_counter()  # Mayor precision temporal
                
                # Esperar fin del eco
                inicio_timeout = time.time()
                while lgpio.gpio_read(h, ECHO_PIN) == 1:
                    if time.time() - inicio_timeout > timeout_fin:
                        raise Exception("Timeout fin eco")
                    time.sleep(0.0000002)  # 0.2μs
                
                fin_eco = time.perf_counter()  # Mayor precision temporal
                
                # Calcular distancia
                duracion = fin_eco - inicio_eco
                distancia_cm = (duracion * velocidad_sonido) / 2
                duracion_us = duracion * 1000000
                
                # Filtrado multiple por etapas
                # 1. Rango fisico razonable
                if not (2.0 <= distancia_cm <= 400.0):
                    lecturas_invalidas += 1
                    continue
                
                # 2. Duracion de pulso razonable
                if not (117 <= duracion_us <= 23324):  # 2cm a 400cm
                    lecturas_invalidas += 1
                    continue
                
                # 3. Validacion de consistencia
                if duracion < 0.0001:  # Menos de 100μs
                    lecturas_invalidas += 1
                    continue
                
                lecturas_cm.append(distancia_cm)
                
                # Mostrar progreso cada 25 lecturas
                if (i + 1) % 25 == 0 and lecturas_cm:
                    media_actual = statistics.mean(lecturas_cm[-25:])
                    print(f"Lectura {i+1}/{NUM_LECTURAS} - Media reciente: {media_actual:.2f} cm")
                
                # Control de timing para completar en tiempo objetivo
                tiempo_transcurrido = time.time() - inicio
                if i < NUM_LECTURAS - 1:
                    tiempo_restante = TIEMPO_TOTAL - tiempo_transcurrido
                    tiempo_entre_lecturas = tiempo_restante / (NUM_LECTURAS - i - 1)
                    # Minimo 50ms entre lecturas para estabilidad
                    time.sleep(max(0.05, min(tiempo_entre_lecturas, 0.08)))
                    
            except Exception as e:
                lecturas_invalidas += 1
                if lecturas_invalidas <= 5:
                    print(f"Error lectura {i+1}: {e}")
                continue
        
        # ANALISIS ESTADISTICO AVANZADO
        if len(lecturas_cm) < 40:
            print(f"Insuficientes lecturas validas: {len(lecturas_cm)}")
            return None
        
        # Convertir a numpy array para analisis
        array_distancias = np.array(lecturas_cm)
        
        # Filtrado por desviacion estandar multiple
        media_inicial = np.mean(array_distancias)
        std_inicial = np.std(array_distancias)
        
        # Primer filtrado: 2.5 sigma
        distancias_filtradas1 = array_distancias[
            abs(array_distancias - media_inicial) <= 2.5 * std_inicial
        ]
        
        if len(distancias_filtradas1) < 30:
            distancias_filtradas1 = array_distancias
        
        # Segundo filtrado: percentiles 10-90
        p10, p90 = np.percentile(distancias_filtradas1, [10, 90])
        distancias_filtradas2 = distancias_filtradas1[
            (distancias_filtradas1 >= p10) & (distancias_filtradas1 <= p90)
        ]
        
        if len(distancias_filtradas2) < 25:
            distancias_filtradas2 = distancias_filtradas1
        
        # Calculo final usando media recortada
        if len(distancias_filtradas2) >= 10:
            # Media del 50% central
            p25, p75 = np.percentile(distancias_filtradas2, [25, 75])
            distancias_finales = distancias_filtradas2[
                (distancias_filtradas2 >= p25) & (distancias_filtradas2 <= p75)
            ]
            distancia_final = statistics.mean(distancias_finales) if len(distancias_finales) > 5 else statistics.median(distancias_filtradas2)
        else:
            distancia_final = statistics.median(distancias_filtradas2)
        
        resultado = 196 - distancia_final
        
        # ESTADISTICAS DETALLADAS
        tiempo_total = time.time() - inicio
        
        print(f"\n--- RESULTADOS DETALLADOS ---")
        print(f"Tiempo total: {tiempo_total:.2f}s")
        print(f"Lecturas totales: {NUM_LECTURAS}")
        print(f"Lecturas validas: {len(lecturas_cm)} ({len(lecturas_cm)/NUM_LECTURAS*100:.1f}%)")
        print(f"Lecturas invalidas: {lecturas_invalidas}")
        print(f"Desviacion estandar: {np.std(distancias_filtradas2):.3f} cm")
        print(f"Distancia medida: {distancia_final:.3f} cm")
        print(f"Rango final: {np.min(distancias_filtradas2):.2f} - {np.max(distancias_filtradas2):.2f} cm")
        print(f"Calculo: 196 - {distancia_final:.3f} = {resultado:.3f}")
        
        return round(resultado, 3)
            
    except Exception as e:
        print(f"Error general: {e}")
        return None
    finally:
        try:
            lgpio.gpiochip_close(h)
        except:
            pass

# Uso directo
if __name__ == "__main__":
    resultado = leer_distancia_promedio()
    if resultado is not None:
        print(f"RESULTADO FINAL: {resultado:.3f}")
    else:
        print("Error en la medicion")
