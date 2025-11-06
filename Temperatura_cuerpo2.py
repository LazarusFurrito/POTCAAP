import time
import board
import busio
import adafruit_mlx90614

def leer_temperatura_promedio():
    """
    Función que lee la temperatura 10 veces y retorna el promedio
    Returns:
        float: Temperatura promedio
    """
    # Inicializar comunicación I2C
    i2c = busio.I2C(board.SCL, board.SDA)
    
    # Crear objeto del sensor
    mlx = adafruit_mlx90614.MLX90614(i2c)
    Temp_tot = 0
    
    for i in range(1, 1001):
        # Leer temperatura del objeto
        temp_object = mlx.object_temperature
        Temp_tot += temp_object
        print(f"Lectura {i}: {temp_object:.2f}°C")
        time.sleep(0.01)
    
    Temp_prom = Temp_tot / 1000
    print(f'La temperatura promedio es {Temp_prom:.2f}°C')
    
    return Temp_prom

def leer_temperatura_instantanea():
    """
    Función que retorna una sola lectura de temperatura
    Returns:
        float: Temperatura instantánea
    """
    i2c = busio.I2C(board.SCL, board.SDA)
    mlx = adafruit_mlx90614.MLX90614(i2c)
    return mlx.object_temperature

# Este bloque solo se ejecuta si el archivo se ejecuta directamente
if __name__ == "__main__":
    # Código que solo se ejecuta cuando runs este archivo directamente
    temperatura = leer_temperatura_promedio()
    print(f"Ejecución directa - Temperatura: {temperatura:.2f}°C")