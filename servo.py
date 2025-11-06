from gpiozero import AngularServo
from time import sleep

# Configurar servo con rango de 0° a 180°
servo = AngularServo(18, min_angle=0, max_angle=180)



servo.angle = 0
print(f"➤ Moviendo a 0°")
sleep(1)
servo.angle = 80
print(f"➤ Moviendo a 80°")
sleep(0.2)
servo.angle = 0
print(f"➤ Moviendo a 0°")
    
  