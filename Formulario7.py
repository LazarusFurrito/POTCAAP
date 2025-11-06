import sys
import random
import string
import subprocess
import threading
import os
import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QMessageBox, QGridLayout, QDialog, QTextEdit,
                            QStackedWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QKeyEvent


class WorkerThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def run(self):
        try:
            self.status.emit("Activando servo...")
            subprocess.run(['python', 'servo.py'], check=True)
            
            self.status.emit("Realizando medición...")
            self.msleep(3000)  # Esperar 3 segundos
            
            # Generar presión simulada
            sistolica = random.randint(110, 130)
            diastolica = random.randint(70, 85)
            presion = f"{sistolica}/{diastolica}"
            
            self.finished.emit(presion)
            
        except subprocess.CalledProcessError as e:
            self.error.emit(f"Error al activar el dispositivo: {e}")
        except FileNotFoundError:
            self.error.emit("No se encontró el archivo servo.py")
        except Exception as e:
            self.error.emit(f"Error inesperado: {e}")


class RotadorThread(QThread):
    finished = pyqtSignal(float)
    error = pyqtSignal(str)

    def run(self):
        try:
            result = subprocess.run(
                ['python3', 'leer_valor.py'], capture_output=True, text=True, check=True
            )
            # Extraer el valor final de la salida
            for line in result.stdout.splitlines():
                if "Valor final leído" in line:
                    valor = float(line.split(":")[-1].strip())
                    self.finished.emit(valor)
                    return
            raise ValueError("No se encontró el valor en la salida.")
        except Exception as e:
            self.error.emit(str(e))


class GestorArchivos:
    @staticmethod
    def guardar_registro(datos_paciente):
        """Guarda los datos del paciente en un archivo TXT"""
        try:
            # Crear directorio de registros si no existe
            directorio = "registros_medicos"
            if not os.path.exists(directorio):
                os.makedirs(directorio)
            
            # Generar nombre de archivo seguro
            nombre_archivo = f"{datos_paciente['nombres']}_{datos_paciente['apellidos']}_{datos_paciente['id_registro']}.txt"
            # Reemplazar caracteres no válidos en nombres de archivo
            nombre_archivo = "".join(c for c in nombre_archivo if c.isalnum() or c in (' ', '-', '_')).rstrip()
            nombre_archivo = nombre_archivo.replace(' ', '_')
            
            ruta_archivo = os.path.join(directorio, nombre_archivo)
            
            # Crear contenido del archivo
            contenido = f"""REGISTRO MÉDICO - {datos_paciente['nombres']} {datos_paciente['apellidos']}
Fecha de registro: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
ID de Registro: {datos_paciente['id_registro']}

INFORMACIÓN PERSONAL:
Nombres: {datos_paciente['nombres']}
Apellidos: {datos_paciente['apellidos']}

DATOS MÉDICOS:
Altura: {datos_paciente['height']} cm
Peso: {datos_paciente['weight']} kg
Temperatura: {datos_paciente['temperature']} °C
Cintura: {datos_paciente['waist']} cm
Cadera: {datos_paciente['hip']} cm
Presión arterial: {datos_paciente['presion']} mm/Hg

Firma del médico: _________________________
"""
            
            # Guardar archivo
            with open(ruta_archivo, 'w', encoding='utf-8') as archivo:
                archivo.write(contenido)
            
            return True, ruta_archivo, nombre_archivo
            
        except Exception as e:
            return False, str(e), None
    
    @staticmethod
    def listar_registros():
        """Lista todos los registros guardados"""
        directorio = "registros_medicos"
        if not os.path.exists(directorio):
            return []
        
        archivos = [f for f in os.listdir(directorio) if f.endswith('.txt')]
        return archivos
    
    @staticmethod
    def cargar_registro(nombre_archivo):
        """Carga un registro desde un archivo"""
        try:
            directorio = "registros_medicos"
            ruta_archivo = os.path.join(directorio, nombre_archivo)
            
            with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
                contenido = archivo.read()
            
            return True, contenido
        except Exception as e:
            return False, str(e)


class FormularioNombres(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.datos_paciente = {}
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Datos del Paciente - Paso 1 de 2")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Título
        titulo = QLabel("Información Personal del Paciente")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo)
        
        # Instrucción
        instruccion = QLabel("Por favor, ingrese la información básica del paciente:")
        instruccion.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        instruccion.setAlignment(Qt.AlignCenter)
        layout.addWidget(instruccion)
        
        # Campos de nombres y apellidos
        form_layout = QGridLayout()
        form_layout.setSpacing(15)
        
        # Nombres (combinando primer y segundo nombre)
        nombres_label = QLabel("Nombres:")
        self.nombres_entry = QLineEdit()
        self.nombres_entry.setPlaceholderText("Ingrese todos los nombres del paciente")
        
        # Apellidos
        apellidos_label = QLabel("Apellidos:")
        self.apellidos_entry = QLineEdit()
        self.apellidos_entry.setPlaceholderText("Ingrese ambos apellidos")
        
        form_layout.addWidget(nombres_label, 0, 0)
        form_layout.addWidget(self.nombres_entry, 0, 1)
        form_layout.addWidget(apellidos_label, 1, 0)
        form_layout.addWidget(self.apellidos_entry, 1, 1)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        # Botones
        botones_layout = QHBoxLayout()
        
        cancelar_btn = QPushButton("Cancelar")
        cancelar_btn.setStyleSheet("QPushButton { background-color: #95a5a6; color: white; font-weight: bold; }")
        cancelar_btn.clicked.connect(self.reject)
        
        continuar_btn = QPushButton("Continuar →")
        continuar_btn.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; }")
        continuar_btn.clicked.connect(self.continuar_formulario)
        
        botones_layout.addWidget(cancelar_btn)
        botones_layout.addWidget(continuar_btn)
        
        layout.addLayout(botones_layout)
        self.setLayout(layout)
        
        self.nombres_entry.setFocus()
    
    def continuar_formulario(self):
        # Validar campos obligatorios
        if not self.nombres_entry.text().strip():
            QMessageBox.warning(self, "Campo requerido", "Por favor ingrese los nombres del paciente")
            self.nombres_entry.setFocus()
            return
            
        if not self.apellidos_entry.text().strip():
            QMessageBox.warning(self, "Campo requerido", "Por favor ingrese los apellidos del paciente")
            self.apellidos_entry.setFocus()
            return
        
        # Guardar datos
        self.datos_paciente['nombres'] = self.nombres_entry.text().strip()
        self.datos_paciente['apellidos'] = self.apellidos_entry.text().strip()
        
        # Abrir formulario médico secuencial
        formulario_secuencial = FormularioSecuencial(self.datos_paciente, self)
        if formulario_secuencial.exec_() == QDialog.Accepted:
            self.accept()


class FormularioSecuencial(QDialog):
    def __init__(self, datos_paciente, parent=None):
        super().__init__(parent)
        self.datos_paciente = datos_paciente
        self.campos_completados = {}
        self.campo_actual = 0
        self.campos_config = [
            ("Altura (cm):", "height", False),
            ("Peso (kg):", "weight", False),
            ("Temperatura (C°):", "temperature", False),
            ("Cintura (cm):", "waist", True),
            ("Cadera (cm):", "hip", True),
            ("Presión arterial (mm/Hg):", "presion", True)
        ]
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle(f"Formulario Médico - Campo 1 de {len(self.campos_config)}")
        self.setFixedSize(800, 650)
        
        self.layout_principal = QVBoxLayout()
        self.layout_principal.setSpacing(20)
        
        # Información del paciente
        self.info_paciente = QLabel(f"Paciente: {self.datos_paciente['nombres']} {self.datos_paciente['apellidos']}")
        self.info_paciente.setStyleSheet("font-weight: bold; color: #2c3e50; background-color: #ecf0f1; padding: 8px; border-radius: 5px;")
        self.layout_principal.addWidget(self.info_paciente)
        
        # Progreso
        self.progreso_label = QLabel()
        self.actualizar_progreso()
        self.layout_principal.addWidget(self.progreso_label)
        
        # Campo actual
        self.campo_layout = QVBoxLayout()
        self.mostrar_campo_actual()
        self.layout_principal.addLayout(self.campo_layout)
        
        self.layout_principal.addStretch()
        
        # Botones de navegación
        self.botones_layout = QHBoxLayout()
        self.setup_botones()
        self.layout_principal.addLayout(self.botones_layout)
        
        self.setLayout(self.layout_principal)
        
    def actualizar_progreso(self):
        progreso = f"Progreso: {self.campo_actual + 1} de {len(self.campos_config)} campos"
        self.progreso_label.setText(progreso)
        self.progreso_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #3498db;")
        self.setWindowTitle(f"Formulario Médico - Campo {self.campo_actual + 1} de {len(self.campos_config)}")
        
    def mostrar_campo_actual(self):
        # Limpiar layout anterior
        for i in reversed(range(self.campo_layout.count())):
            widget = self.campo_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        nombre_campo, clave, tiene_boton = self.campos_config[self.campo_actual]
        
        # Etiqueta del campo
        label = QLabel(nombre_campo)
        label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        self.campo_layout.addWidget(label)
        
        # Layout para entrada y botón
        entrada_layout = QHBoxLayout()
        
        # Campo de entrada
        self.entrada_actual = QLineEdit()
        self.entrada_actual.setPlaceholderText(f"Ingrese {nombre_campo.lower()}")
        
        # Si es un campo previamente completado, mostrar el valor
        if clave in self.campos_completados:
            self.entrada_actual.setText(self.campos_completados[clave])
        
        entrada_layout.addWidget(self.entrada_actual)
        
        # Botón de medición si corresponde
        if tiene_boton:
            boton_medir = QPushButton("Medir")
            boton_medir.setStyleSheet("background-color: #2e86de; color: white; font-weight: bold;")
            
            if clave == "presion":
                boton_medir.clicked.connect(self.medir_presion)
            else:
                boton_medir.clicked.connect(self.medir_circunferencia)
                
            entrada_layout.addWidget(boton_medir)
        
        self.campo_layout.addLayout(entrada_layout)
        self.entrada_actual.setFocus()
        
    def setup_botones(self):
        # Limpiar botones anteriores
        for i in reversed(range(self.botones_layout.count())):
            widget = self.botones_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        boton_anterior = QPushButton("← Anterior")
        boton_anterior.setStyleSheet("QPushButton { background-color: #95a5a6; color: white; font-weight: bold; }")
        boton_anterior.clicked.connect(self.campo_anterior)
        boton_anterior.setEnabled(self.campo_actual > 0)
        
        if self.campo_actual < len(self.campos_config) - 1:
            boton_siguiente = QPushButton("Siguiente →")
            boton_siguiente.setStyleSheet("QPushButton { background-color: #3498db; color: white; font-weight: bold; }")
            boton_siguiente.clicked.connect(self.campo_siguiente)
        else:
            boton_siguiente = QPushButton("Guardar Registro")
            boton_siguiente.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; }")
            boton_siguiente.clicked.connect(self.finalizar_formulario)
        
        self.botones_layout.addWidget(boton_anterior)
        self.botones_layout.addWidget(boton_siguiente)
        
    def campo_anterior(self):
        if self.campo_actual > 0:
            # Guardar campo actual
            self.guardar_campo_actual()
            self.campo_actual -= 1
            self.actualizar_interfaz()
        
    def campo_siguiente(self):
        # Validar campo actual
        if not self.entrada_actual.text().strip():
            QMessageBox.warning(self, "Campo requerido", f"Por favor ingrese {self.campos_config[self.campo_actual][0].lower()}")
            self.entrada_actual.setFocus()
            return
            
        # Guardar campo actual
        self.guardar_campo_actual()
        
        if self.campo_actual < len(self.campos_config) - 1:
            self.campo_actual += 1
            self.actualizar_interfaz()
        
    def guardar_campo_actual(self):
        clave = self.campos_config[self.campo_actual][1]
        self.campos_completados[clave] = self.entrada_actual.text().strip()
        
    def actualizar_interfaz(self):
        self.actualizar_progreso()
        self.mostrar_campo_actual()
        self.setup_botones()
        
    def medir_circunferencia(self):
        self.entrada_actual.setText("Midiendo...")
        self.rotador_thread = RotadorThread()
        self.rotador_thread.finished.connect(lambda valor: self.mostrar_medida_circunferencia(valor))
        self.rotador_thread.error.connect(self.error_medida)
        self.rotador_thread.start()
        
    def mostrar_medida_circunferencia(self, valor):
        self.entrada_actual.setText(f"{valor:.2f}")
        QMessageBox.information(self, "Medición completa", f"Medida registrada: {valor:.2f} cm")
        
    def medir_presion(self):
        self.entrada_actual.setText("Coloque el brazalete...")
        self.worker = WorkerThread()
        self.worker.finished.connect(self.mostrar_presion)
        self.worker.error.connect(self.error_medida)
        self.worker.status.connect(self.actualizar_estado_presion)
        self.worker.start()
        
    def actualizar_estado_presion(self, mensaje):
        self.entrada_actual.setText(mensaje)
        
    def mostrar_presion(self, presion):
        self.entrada_actual.setText(presion)
        QMessageBox.information(self, "Medición Completa", f"Presión medida: {presion} mm/Hg")
        
    def error_medida(self, mensaje_error):
        self.entrada_actual.clear()
        QMessageBox.critical(self, "Error", mensaje_error)
        
    def finalizar_formulario(self):
        # Guardar último campo
        self.guardar_campo_actual()
        
        # Validar que todos los campos estén completos
        campos_faltantes = []
        for nombre, clave, _ in self.campos_config:
            if not self.campos_completados.get(clave):
                campos_faltantes.append(nombre)
                
        if campos_faltantes:
            QMessageBox.warning(self, "Campos incompletos", 
                              f"Por favor complete los siguientes campos:\n" + "\n".join(f"• {campo}" for campo in campos_faltantes))
            return
            
        # Generar ID de registro
        id_registro = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        # Combinar todos los datos
        datos_completos = {
            'nombres': self.datos_paciente['nombres'],
            'apellidos': self.datos_paciente['apellidos'],
            'id_registro': id_registro,
            **self.campos_completados
        }
        
        # Guardar en archivo
        exito, resultado, nombre_archivo = GestorArchivos.guardar_registro(datos_completos)
        
        if exito:
            # Mostrar resumen
            resumen = f"""
            REGISTRO MÉDICO GUARDADO EXITOSAMENTE
            
            Paciente: {datos_completos['nombres']} {datos_completos['apellidos']}
            ID de Registro: {datos_completos['id_registro']}
            Archivo guardado: {nombre_archivo}
            Ubicación: {resultado}
            
            Datos médicos:
            - Altura: {datos_completos['height']} cm
            - Peso: {datos_completos['weight']} kg
            - Temperatura: {datos_completos['temperature']} °C
            - Cintura: {datos_completos['waist']} cm
            - Cadera: {datos_completos['hip']} cm
            - Presión arterial: {datos_completos['presion']} mm/Hg
            """
            
            print("=== REGISTRO MÉDICO GUARDADO ===")
            for key, value in datos_completos.items():
                print(f"{key}: {value}")
            print(f"Archivo: {nombre_archivo}")
            print("================================")
            
            QMessageBox.information(self, "Éxito", 
                                  f"Registro médico guardado correctamente\n\n"
                                  f"Archivo: {nombre_archivo}\n"
                                  f"ID: {datos_completos['id_registro']}")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", 
                               f"No se pudo guardar el registro:\n{resultado}")
            return


class InformacionProyectoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Información del Proyecto")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Título
        titulo = QLabel("Información del Proyecto")
        titulo.setStyleSheet("font-size: 20px; font-weight: bold; margin: 10px;")
        titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo)
        
        # Información del proyecto
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setPlainText(
            "SISTEMA DE REGISTRO MÉDICO AUTOMATIZADO\n\n"
            "Descripción:\n"
            "Este sistema permite la captura automatizada de datos médicos "
            "integrando dispositivos de medición como sensores de presión arterial "
            "y medidores de circunferencia corporal.\n\n"
            
            "Funcionalidades:\n"
            "• Captura de datos del paciente\n"
            "• Medición automática de presión arterial\n"
            "• Medición de circunferencias corporales\n"
            "• Generación automática de ID de registro\n"
            "• Almacenamiento en archivos TXT\n"
            "• Gestión de registros médicos\n\n"
            
            "Tecnologías utilizadas:\n"
            "• Python 3.x\n"
            "• PyQt5 para la interfaz gráfica\n"
            "• Dispositivos de medición conectados\n"
            "• Sistema de archivos para almacenamiento\n\n"
            
            "Versión: 1.1.0\n"
            "Desarrollado por: Equipo de Desarrollo Médico"
        )
        layout.addWidget(info_text)
        
        # Botón cerrar
        cerrar_btn = QPushButton("Cerrar")
        cerrar_btn.clicked.connect(self.accept)
        cerrar_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; font-weight: bold; }")
        layout.addWidget(cerrar_btn)
        
        self.setLayout(layout)


class MenuRegistros(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Sistema de Registros Médicos")
        self.setFixedSize(400, 450)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        # Título
        titulo = QLabel("Menú Principal")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size: 18px; font-weight: bold; margin: 20px;")
        layout.addWidget(titulo)
        
        # Instrucciones de teclas
        instrucciones = QLabel("Presione 1-6 para navegar o use el mouse")
        instrucciones.setAlignment(Qt.AlignCenter)
        instrucciones.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 10px;")
        layout.addWidget(instrucciones)
        
        # Botones del menú
        botones = [
            ("1. Crear Registro", self.crear_registro),
            ("2. Modificar Registro", self.modificar_registro),
            ("3. Eliminar Registro", self.eliminar_registro),
            ("4. Buscar Registro", self.buscar_registro),
            ("5. Información del Proyecto", self.mostrar_informacion),
            ("6. Salir", self.salir)
        ]
        
        for texto, funcion in botones:
            boton = QPushButton(texto)
            boton.setFixedSize(250, 50)
            if texto == "6. Salir":
                boton.setStyleSheet("QPushButton { background-color: #ff6b6b; color: white; font-weight: bold; }")
            elif texto == "5. Información del Proyecto":
                boton.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; font-weight: bold; }")
            else:
                boton.setStyleSheet("QPushButton { background-color: #4e73df; color: white; font-weight: bold; }")
            boton.clicked.connect(funcion)
            layout.addWidget(boton, alignment=Qt.AlignCenter)
        
        central_widget.setLayout(layout)
        
    def keyPressEvent(self, event: QKeyEvent):
        """Maneja las teclas presionadas"""
        key = event.key()
        
        if key == Qt.Key_1:
            self.crear_registro()
        elif key == Qt.Key_2:
            self.modificar_registro()
        elif key == Qt.Key_3:
            self.eliminar_registro()
        elif key == Qt.Key_4:
            self.buscar_registro()
        elif key == Qt.Key_5:
            self.mostrar_informacion()
        elif key == Qt.Key_6:
            self.salir()
        else:
            super().keyPressEvent(event)
        
    def crear_registro(self):
        """Abre primero el formulario de nombres y apellidos"""
        formulario_nombres = FormularioNombres(self)
        if formulario_nombres.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Proceso completado", "Registro médico creado y guardado exitosamente")
        
    def modificar_registro(self):
        QMessageBox.information(self, "Información", "Función 'Modificar Registro' no implementada aún")
        
    def eliminar_registro(self):
        QMessageBox.information(self, "Información", "Función 'Eliminar Registro' no implementada aún")
        
    def buscar_registro(self):
        QMessageBox.information(self, "Información", "Función 'Buscar Registro' no implementada aún")
        
    def mostrar_informacion(self):
        """Muestra el diálogo de información del proyecto"""
        info_dialog = InformacionProyectoDialog(self)
        info_dialog.exec_()
        
    def salir(self):
        respuesta = QMessageBox.question(
            self, 
            "Salir", 
            "¿Está seguro que desea salir?\n\nSe mostrará la información del proyecto antes de salir.",
            QMessageBox.Yes | QMessageBox.No
        )
        if respuesta == QMessageBox.Yes:
            # Mostrar información del proyecto antes de salir
            info_dialog = InformacionProyectoDialog(self)
            info_dialog.exec_()
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Estilo moderno
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f8f9fc;
        }
        QPushButton {
            border: none;
            border-radius: 5px;
            padding: 10px;
            font-size: 14px;
        }
        QPushButton:hover {
            opacity: 0.9;
        }
        QLineEdit {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        QLineEdit:focus {
            border: 2px solid #3498db;
        }
        QLabel {
            font-size: 14px;
            font-weight: bold;
        }
        QTextEdit {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            font-size: 12px;
        }
    """)
    
    ventana = MenuRegistros()
    ventana.show()
    sys.exit(app.exec_())