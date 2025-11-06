import Temperatura_cuerpo2


# Ejecutar el programa principal del encoder y capturar el valor retornado
valor_final = Temperatura_cuerpo2.leer_temperatura_promedio()

# Imprimir el resultado
print(f"\nValor final leído del mlx90614: {valor_final:.2f}")