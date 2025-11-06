from Bascula2 import leer_peso_promediado

# Ejecutar automáticamente las 100 mediciones y obtener promedio
peso = leer_peso_promediado(100)
print(f"Peso: {peso:.2f} kg")
