import lgpio
import time
import json
import os

class HX711_LGPIO:
    def __init__(self, dout, pd_sck, gain=128):
        self.DOUT = dout
        self.PD_SCK = pd_sck
        self.GAIN = gain
        self.OFFSET = 0
        self.SCALE = 1
        
        # Abrir conexión con lgpio
        self.h = lgpio.gpiochip_open(0)
        
        # Configurar pines
        lgpio.gpio_claim_input(self.h, self.DOUT)
        lgpio.gpio_claim_output(self.h, self.PD_SCK)
        
        self.power_down()
        self.power_up()
        
    def power_down(self):
        lgpio.gpio_write(self.h, self.PD_SCK, 0)
        lgpio.gpio_write(self.h, self.PD_SCK, 1)
        time.sleep(0.0001)
        
    def power_up(self):
        lgpio.gpio_write(self.h, self.PD_SCK, 0)
        
    def is_ready(self):
        return lgpio.gpio_read(self.h, self.DOUT) == 0
        
    def read(self):
        # Esperar hasta que el sensor esté listo
        timeout = time.time() + 0.5  # Timeout de 500ms
        while not self.is_ready():
            if time.time() > timeout:
                raise Exception("Timeout esperando sensor HX711")
            time.sleep(0.001)
        
        # Leer los 24 bits de datos
        data = 0
        for i in range(24):
            lgpio.gpio_write(self.h, self.PD_SCK, 1)
            lgpio.gpio_write(self.h, self.PD_SCK, 0)
            bit = lgpio.gpio_read(self.h, self.DOUT)
            data = (data << 1) | bit
        
        # Configurar la ganancia para la siguiente lectura
        for i in range(self.GAIN):
            lgpio.gpio_write(self.h, self.PD_SCK, 1)
            lgpio.gpio_write(self.h, self.PD_SCK, 0)
        
        # Convertir a signed integer (complemento a 2)
        if data & 0x800000:  # Si es negativo
            data = data - 0x1000000
        
        return data
    
    def get_value(self, times=3):
        values = []
        for i in range(times):
            try:
                values.append(self.read())
            except Exception as e:
                print(f"Error en lectura {i+1}: {e}")
                continue
            time.sleep(0.1)
        
        if not values:
            raise Exception("No se pudieron obtener lecturas válidas")
        
        return sum(values) / len(values)
    
    def get_units(self, times=3):
        return (self.get_value(times) - self.OFFSET) / self.SCALE
    
    def tare(self, times=15):
        self.OFFSET = self.get_value(times)
    
    def set_scale(self, scale):
        self.SCALE = scale
    
    def set_offset(self, offset):
        self.OFFSET = offset
    
    def close(self):
        lgpio.gpiochip_close(self.h)

class BalanzaPi5:
    def __init__(self, dout_pin=5, pd_sck_pin=6, archivo_calibracion="calibracion.json"):
        self.dout_pin = dout_pin
        self.pd_sck_pin = pd_sck_pin
        self.archivo_calibracion = archivo_calibracion
        
        print("Inicializando HX711 en Raspberry Pi 5...")
        self.hx = HX711_LGPIO(dout_pin, pd_sck_pin)
        
        self.cargar_calibracion()
        print("Balanza lista")

    def cargar_calibracion(self):
        if os.path.exists(self.archivo_calibracion):
            try:
                with open(self.archivo_calibracion, 'r') as f:
                    datos = json.load(f)
                    self.hx.set_offset(datos['offset'])
                    self.hx.set_scale(datos['scale'])
                print(f"Calibracion cargada - Offset: {self.hx.OFFSET}, Escala: {self.hx.SCALE}")
            except Exception as e:
                print(f"Error cargando calibracion: {e}")
                print("Usando valores por defecto")
                self.hx.set_offset(0)
                self.hx.set_scale(1)
        else:
            print("No hay calibracion previa. Usar opcion de calibracion.")

    def guardar_calibracion(self):
        datos = {
            'offset': self.hx.OFFSET,
            'scale': self.hx.SCALE
        }
        with open(self.archivo_calibracion, 'w') as f:
            json.dump(datos, f, indent=4)
        print("Calibracion guardada")

    def calibrar(self):
        print("\n" + "="*50)
        print("CALIBRACION DE BALANZA")
        print("="*50)
        
        print("Paso 1/2: Tara (cero)")
        print("Retira todo peso de la balanza")
        input("Presiona Enter cuando este vacia...")
        
        print("Realizando tara...")
        try:
            self.hx.tare(10)
            print(f"Offset establecido: {self.hx.OFFSET}")
        except Exception as e:
            print(f"Error en tara: {e}")
            return
        
        print("\nPaso 2/2: Peso conocido")
        try:
            peso_conocido = float(input("Ingresa el peso conocido en gramos: "))
        except:
            print("Peso no valido")
            return
            
        input(f"Coloca {peso_conocido}g y presiona Enter...")
        
        print("Calculando escala...")
        try:
            valor = self.hx.get_value(10)
            escala = (valor - self.hx.OFFSET) / peso_conocido
            self.hx.set_scale(escala)
            
            self.guardar_calibracion()
            
            print(f"\nCalibracion completada exitosamente!")
            print(f"Offset: {self.hx.OFFSET}")
            print(f"Escala: {escala}")
            
            # Verificar calibracion
            peso_verificado = self.leer_peso()
            if peso_verificado:
                print(f"Peso verificado: {peso_verificado:.1f} g")
                
        except Exception as e:
            print(f"Error en calibracion: {e}")

    def tara(self):
        print("Realizando tara...")
        try:
            self.hx.tare(10)
            self.guardar_calibracion()
            print("Tara completada")
        except Exception as e:
            print(f"Error en tara: {e}")

    def leer_peso(self, muestras=5):
        try:
            peso = self.hx.get_units(muestras)
            return max(0, peso)
        except Exception as e:
            print(f"Error leyendo peso: {e}")
            return None

    def prueba_sensor(self):
        print("\nMODO PRUEBA - Valores crudos del HX711")
        print("Presiona Ctrl+C para detener")
        print("-" * 40)
        
        try:
            contador = 0
            while True:
                try:
                    valor_crudo = self.hx.read()
                    peso = self.leer_peso(1) if contador % 5 == 0 else None
                    
                    if peso is not None:
                        print(f"Crudo: {valor_crudo:8d} | Peso: {peso:6.1f} g")
                    else:
                        print(f"Crudo: {valor_crudo:8d}")
                    
                    contador += 1
                    time.sleep(0.2)
                    
                except Exception as e:
                    print(f"Error en lectura: {e}")
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            print("\nPrueba terminada")

    def modo_continuo(self):
        print("\nMODO CONTINUO - Lecturas de peso")
        print("Presiona Ctrl+C para detener")
        print("-" * 30)
        
        try:
            while True:
                peso = self.leer_peso(3)
                if peso is not None:
                    print(f"Peso: {peso:6.1f} g")
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nModo continuo terminado")

    def menu_principal(self):
        try:
            while True:
                print("\n" + "="*40)
                print("BALANZA HX711 - RASPBERRY PI 5")
                print("="*40)
                print("1. Calibrar balanza")
                print("2. Tara (poner en cero)")
                print("3. Leer peso actual")
                print("4. Modo continuo")
                print("5. Prueba de sensor (valores crudos)")
                print("6. Salir")
                
                opcion = input("\nSelecciona opcion (1-6): ").strip()
                
                if opcion == "1":
                    self.calibrar()
                elif opcion == "2":
                    self.tara()
                elif opcion == "3":
                    peso = self.leer_peso()
                    if peso is not None:
                        print(f"\n>>> Peso actual: {peso:.1f} g <<<")
                    else:
                        print("Error al leer el peso")
                elif opcion == "4":
                    self.modo_continuo()
                elif opcion == "5":
                    self.prueba_sensor()
                elif opcion == "6":
                    break
                else:
                    print("Opcion no valida")
                    
        except KeyboardInterrupt:
            print("\nPrograma terminado por el usuario")
        finally:
            self.hx.close()
            print("Recursos liberados")

# Configuracion
if __name__ == "__main__":
    # Pines por defecto - puedes cambiarlos
    DOUT_PIN = 5   # GPIO 5
    PD_SCK_PIN = 6 # GPIO 6
    
    print("CONFIGURACION HX711 PARA RASPBERRY PI 5")
    print(f"DOUT (DT): GPIO {DOUT_PIN}")
    print(f"SCK: GPIO {PD_SCK_PIN}")
    print("Asegurate de que los pines esten correctamente conectados")
    
    balanza = BalanzaPi5(dout_pin=DOUT_PIN, pd_sck_pin=PD_SCK_PIN)
    balanza.menu_principal()