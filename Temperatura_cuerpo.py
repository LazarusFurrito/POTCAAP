import time
import board
import busio
import adafruit_mlx90614

# Inicializar comunicación I2C
i2c = busio.I2C(board.SCL, board.SDA)

# Crear objeto del sensor
mlx = adafruit_mlx90614.MLX90614(i2c)
Temp_tot=0
Temp_prom=0

for i in range(1,1001):
    # Leer temperatura del objeto (lo que apunta el sensor)
    temp_object = mlx.object_temperature
        
        # Leer temperatura ambiente
    temp_ambient = mlx.ambient_temperature
        
    Temp_tot+=temp_object
        
    #print(i)
        
    time.sleep(0.01)
    
Temp_prom=Temp_tot/1000


print(f'La temperatura promedio es {Temp_prom:.2f}')


##return Temp_prom
