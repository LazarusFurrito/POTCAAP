import lgpio
import time

# Pines
DOUT = 5
SCK = 6

# Valores de calibración predefinidos (usa tus valores reales)
OFFSET = 131640  # Tu offset anterior que funciona
CALIBRATION_FACTOR = 23000.0  # Ajusta este valor según necesites

# Crear handle para GPIO
h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_input(h, DOUT)
lgpio.gpio_claim_output(h, SCK)

def read_raw():
    """Lee 24 bits del HX711 (modo canal A, ganancia 128)."""
    # Esperar a que el HX711 esté listo (DOUT = LOW)
    while lgpio.gpio_read(h, DOUT) == 1:
        time.sleep(0.001)

    count = 0
    # Leer 24 bits
    for _ in range(24):
        lgpio.gpio_write(h, SCK, 1)
        count = (count << 1) | lgpio.gpio_read(h, DOUT)
        lgpio.gpio_write(h, SCK, 0)

    # Un pulso extra para seleccionar canal A (ganancia 128)
    lgpio.gpio_write(h, SCK, 1)
    lgpio.gpio_write(h, SCK, 0)

    # Convertir a número con signo (24 bits)
    if count & 0x800000:
        count -= 0x1000000

    return count

def leer_peso_promediado(mediciones=100):
    """Toma múltiples mediciones y devuelve el promedio automáticamente."""
    print(f"Iniciando medición automática de {mediciones} muestras...")
    
    pesos = []
    raw_values = []
    
    for i in range(mediciones):
        try:
            raw_val = read_raw()
            peso = (raw_val - OFFSET) / CALIBRATION_FACTOR
            
            pesos.append(peso)
            raw_values.append(raw_val)
            
            # Mostrar progreso
            if (i + 1) % 20 == 0:
                print(f"Progreso: {i + 1}/{mediciones} mediciones")
            
            time.sleep(0.05)  # Pausa corta entre mediciones
            
        except Exception as e:
            print(f"Error en medición {i + 1}: {e}")
    
    if pesos:
        # Calcular resultados
        peso_promedio = sum(pesos) / len(pesos)
        raw_promedio = sum(raw_values) / len(raw_values)
        
        # Calcular precisión
        diferencia_max = max(pesos) - min(pesos)
        
        print(f"\n=== RESULTADOS ===")
        print(f"Raw promedio: {raw_promedio:.0f}")
        print(f"Peso promedio: {peso_promedio:.4f} kg")
        print(f"Rango de variación: {diferencia_max:.4f} kg")
        print(f"Offset usado: {OFFSET}")
        print(f"Factor usado: {CALIBRATION_FACTOR}")
        
        return peso_promedio
    else:
        print("❌ No se pudieron completar las mediciones")
        return 0.0

# --- Ejecución automática al iniciar ---
if __name__ == "__main__":
    try:
        # Tomar 100 mediciones automáticamente y obtener promedio
        peso_final = leer_peso_promediado(100)
        
        # Mostrar resultado final (lo que espera Bascula3.py)
        print(f"\n✅ Peso final: {peso_final:.3f} kg")
        
    except Exception as e:
        print(f"Error durante la medición: {e}")
        peso_final = 0.0
    
    finally:
        # Limpiar GPIO
        lgpio.gpiochip_close(h)
    
    # El valor queda disponible para ser importado
    # o se imprime como requiere Bascula3.py
