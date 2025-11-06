import time
import board
import busio
import adafruit_mlx90614

# Inicializar comunicación I2C
i2c = busio.I2C(board.SCL, board.SDA)

# Crear objeto del sensor
mlx = adafruit_mlx90614.MLX90614(i2c)

try:
    while True:
        # Leer temperatura del objeto (lo que apunta el sensor)
        temp_object = mlx.object_temperature
        
        # Leer temperatura ambiente
        temp_ambient = mlx.ambient_temperature
        
        print(f"Temperatura del objeto: {temp_object:.2f}°C")
        print(f"Temperatura ambiente: {temp_ambient:.2f}°C")
        print("-" * 30)
        
        time.sleep(1)

except KeyboardInterrupt:
    print("\nPrograma terminado")