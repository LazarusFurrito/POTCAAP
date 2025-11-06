#!/usr/bin/env python3
import lgpio
import time
import sys

class KY040:
    def __init__(self, clk_pin, dt_pin, sw_pin=None):
        self.clk_pin = clk_pin
        self.dt_pin = dt_pin
        self.sw_pin = sw_pin
        self.counter = 0
        self.last_clk_state = 0
        self.last_sw_state = 0
        
        # Inicializar conexión con lgpio
        self.h = lgpio.gpiochip_open(0)
        
        # Configurar pines
        lgpio.gpio_claim_input(self.h, clk_pin)
        lgpio.gpio_claim_input(self.h, dt_pin)
        if sw_pin is not None:
            lgpio.gpio_claim_input(self.h, sw_pin)
        
        # Leer estado inicial
        self.last_clk_state = lgpio.gpio_read(self.h, clk_pin)
        if sw_pin is not None:
            self.last_sw_state = lgpio.gpio_read(self.h, sw_pin)
    
    def read_rotation(self):
        """Lee la rotación del encoder y actualiza el contador"""
        clk_state = lgpio.gpio_read(self.h, self.clk_pin)
        
        if clk_state != self.last_clk_state:
            dt_state = lgpio.gpio_read(self.h, self.dt_pin)
            
            if dt_state != clk_state:
                # Rotación en sentido horario
                self.counter += 1
                direction = "HORARIO"
            else:
                # Rotación en sentido antihorario
                self.counter -= 1
                direction = "ANTIHORARIO"
            
            self.last_clk_state = clk_state
            return direction
        
        return None
    
    def read_button(self):
        """Lee el estado del botón (si está conectado)"""
        if self.sw_pin is None:
            return None
        
        sw_state = lgpio.gpio_read(self.h, self.sw_pin)
        
        # Detectar flanco descendente (botón presionado)
        if sw_state == 0 and self.last_sw_state == 1:
            self.last_sw_state = sw_state
            return True
        
        self.last_sw_state = sw_state
        return False
    
    def get_counter(self):
        """Retorna el valor actual del contador"""
        return self.counter * 0.51
    
    def cleanup(self):
        """Limpia los recursos de lgpio"""
        lgpio.gpiochip_close(self.h)

# Ejemplo de uso básico
def main():
    # Configurar pines (ajusta según tu conexión)
    CLK_PIN = 20    
    DT_PIN = 21       
    SW_PIN = 26    # Pin SW del KY040 (opcional)
    
    encoder = KY040(CLK_PIN, DT_PIN, SW_PIN)
    
    print("Controlador KY040 iniciado")
    print("Gira el encoder o presiona el botón")
    print("Ejecución automática por 30 segundos...\n")

    inicio = time.time()
    duracion = 30  # segundos

    try:
        while time.time() - inicio < duracion:
            # Leer rotación
            direction = encoder.read_rotation()
            if direction:
                print(f"Rotación: {direction} - Contador: {encoder.get_counter():.2f}")
            
            # Leer botón
            if encoder.read_button():
                print("Botón presionado!")
                # encoder.counter = 0  # opcional
            
            time.sleep(0.01)
        
        print("\nTiempo máximo alcanzado (30 s). Finalizando...")
        return encoder.get_counter()

    finally:
        encoder.cleanup()

if __name__ == "__main__":
    main()