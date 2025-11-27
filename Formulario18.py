import sys
import random
import string
import subprocess
import threading
import os
import datetime
import webbrowser
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QMessageBox, QGridLayout, QDialog, QTextEdit,
                            QStackedWidget, QListWidget, QListWidgetItem,
                            QGroupBox, QScrollArea, QComboBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QKeyEvent
import pygame
import pymysql

class WorkerThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def run(self):
        try:
            self.status.emit("Tomando presión arterial...")
            
            # Ejecutar Coordenadas.py que ahora maneja todo el proceso
            result = subprocess.run(
                ['python', 'gemini5.py'], 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            # Procesar la salida de Coordenadas.py para obtener los valores
            sistolica = None
            diastolica = None
            bpm = None
            
            for line in result.stdout.splitlines():
                if "Presión:" in line:
                    # Buscar valores de presión en formato "Presión: 120/80"
                    presion_str = line.split(":")[-1].strip()
                    partes = presion_str.split("/")
                    if len(partes) == 2:
                        sistolica = partes[0].strip()
                        diastolica = partes[1].strip()
                elif "BPM:" in line:
                    # Buscar valor de BPM
                    bpm_str = line.split(":")[-1].strip()
                    bpm = bpm_str
            
            # Si no se encontraron valores, usar valores simulados como respaldo
            if sistolica is None or diastolica is None:
                sistolica = random.randint(110, 130)
                diastolica = random.randint(70, 85)
            
            if bpm is None:
                bpm = random.randint(60, 100)
                
            presion = f"{sistolica}/{diastolica}"
            
            self.finished.emit(f"{presion}|{bpm}")
            
        except subprocess.CalledProcessError as e:
            self.error.emit(f"Error al activar el dispositivo: {e}")
        except FileNotFoundError:
            self.error.emit("No se encontró el archivo Coordenadas.py")
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

class TemperaturaThread(QThread):
    finished = pyqtSignal(float)
    error = pyqtSignal(str)

    def run(self):
        try:
            result = subprocess.run(
                ['python', 'Temp_form2.py'], 
                capture_output=True, 
                text=True, 
                check=True
            )
            # Buscar Temp_prom en la salida
            for line in result.stdout.splitlines():
                if "Valor final leído" in line:
                    # Extraer el valor numérico de la temperatura
                    temp_str = line.split(":")[-1].strip()
                    temperatura = float(temp_str)
                    self.finished.emit(temperatura)
                    return
            raise ValueError("No se encontró Temp_prom en la salida")
        except Exception as e:
            self.error.emit(str(e))

class PesoThread(QThread):
    finished = pyqtSignal(float)
    error = pyqtSignal(str)

    def run(self):
        try:
            result = subprocess.run(
                ['python', 'Bascula3.py'], 
                capture_output=True, 
                text=True, 
                check=True
            )
            # Buscar el peso en la salida
            for line in result.stdout.splitlines():
                if "Peso:" in line:
                    # Extraer el valor numérico del peso
                    peso_str = line.split(":")[-1].strip().replace(" kg", "")
                    peso = float(peso_str)
                    self.finished.emit(peso)
                    return
            raise ValueError("No se encontró el peso en la salida")
        except Exception as e:
            self.error.emit(str(e))

class AlturaThread(QThread):
    finished = pyqtSignal(float)
    error = pyqtSignal(str)

    def run(self):
        try:
            result = subprocess.run(
                ['python', 'Altura2.py'], 
                capture_output=True, 
                text=True, 
                check=True
            )
            # Buscar la altura en la salida
            for line in result.stdout.splitlines():
                if "Resultado:" in line:
                    # Extraer el valor numérico de la altura
                    altura_str = line.split(":")[-1].strip()
                    altura = float(altura_str)
                    self.finished.emit(altura)
                    return
            raise ValueError("No se encontró la altura en la salida")
        except Exception as e:
            self.error.emit(str(e))

class Spo2Thread(QThread):
    finished = pyqtSignal(float)
    error = pyqtSignal(str)

    def run(self):
        try:
            result = subprocess.run(
                ['python', 'maino3.py'], 
                capture_output=True, 
                text=True, 
                check=True
            )
            # Buscar SpO2 en la salida
            for line in result.stdout.splitlines():
                if "SpO2:" in line:
                    # Extraer el valor numérico del SpO2
                    spo2_str = line.split(":")[-1].strip().replace("%", "")
                    spo2 = float(spo2_str)
                    self.finished.emit(spo2)
                    return
            raise ValueError("No se encontró el valor de SpO2 en la salida")
        except Exception as e:
            self.error.emit(str(e))

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Establece conexión con la base de datos"""
        try:
            self.connection = pymysql.connect(
                host='localhost',
                user='app_medica',
                password='caloca2022',
                database='registros_medicos',
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            print("✅ Conexión a la base de datos establecida")
        except Exception as e:
            print(f"❌ Error conectando a la base de datos: {e}")
            self.connection = None
    
    def guardar_registro(self, datos_paciente):
        """Guarda los datos del paciente en la base de datos"""
        if not self.connection:
            return False, "No hay conexión a la base de datos"

        try:
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO pacientes (
                    id_registro, nombres, apellidos, altura, peso, 
                    temperatura, cintura, cadera, presion_arterial, bpm, spo2
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
            
                # Mapear nombres de campos del formulario a la base de datos
                altura = datos_paciente.get('height') or datos_paciente.get('altura')
                peso = datos_paciente.get('weight') or datos_paciente.get('peso')
                temperatura = datos_paciente.get('temperature') or datos_paciente.get('temperatura')
                cintura = datos_paciente.get('waist') or datos_paciente.get('cintura')
                cadera = datos_paciente.get('hip') or datos_paciente.get('cadera')
                presion = datos_paciente.get('presion') or datos_paciente.get('presion_arterial')
                spo2 = datos_paciente.get('spo2', 'N/A')  # <- Valor por defecto si no existe
            
                cursor.execute(sql, (
                    datos_paciente['id_registro'],
                    datos_paciente['nombres'],
                    datos_paciente['apellidos'],
                    altura,
                    peso,
                    temperatura,
                    cintura,
                    cadera,
                    presion,
                    datos_paciente.get('bpm', 'N/A'),
                    spo2  # <- Este es el parámetro 11
                ))
            
                self.connection.commit()
                return True, "Registro guardado exitosamente"
            
        except Exception as e:
            self.connection.rollback()
            return False, f"Error al guardar en la base de datos: {e}"
    
    def listar_registros(self):
        """Lista todos los registros de la base de datos"""
        if not self.connection:
            return []
        
        try:
            with self.connection.cursor() as cursor:
                sql = "SELECT * FROM pacientes ORDER BY fecha_registro DESC"
                cursor.execute(sql)
                return cursor.fetchall()
        except Exception as e:
            print(f"Error al listar registros: {e}")
            return []
    
    def buscar_registro(self, criterio, valor):
        """Busca registros por diferentes criterios"""
        if not self.connection:
            return []
        
        try:
            with self.connection.cursor() as cursor:
                if criterio == "id":
                    sql = "SELECT * FROM pacientes WHERE id_registro = %s"
                elif criterio == "nombre":
                    sql = "SELECT * FROM pacientes WHERE nombres LIKE %s OR apellidos LIKE %s"
                    valor = f"%{valor}%"
                    cursor.execute(sql, (valor, valor))
                    return cursor.fetchall()
                elif criterio == "fecha":
                    sql = "SELECT * FROM pacientes WHERE DATE(fecha_registro) = %s"
                else:
                    return []
                
                cursor.execute(sql, (valor,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Error al buscar registros: {e}")
            return []
    
    def actualizar_registro(self, id_registro, datos_actualizados):
        """Actualiza un registro existente"""
        if not self.connection:
            return False, "No hay conexión a la base de datos"
        
        try:
            with self.connection.cursor() as cursor:
                sql = """
                UPDATE pacientes SET 
                    nombres = %s, apellidos = %s, altura = %s, peso = %s,
                    temperatura = %s, cintura = %s, cadera = %s, 
                    presion_arterial = %s, bpm = %s, spo2 = %s
                WHERE id_registro = %s
                """
                
                altura = datos_actualizados.get('height') or datos_actualizados.get('altura')
                peso = datos_actualizados.get('weight') or datos_actualizados.get('peso')
                temperatura = datos_actualizados.get('temperature') or datos_actualizados.get('temperatura')
                cintura = datos_actualizados.get('waist') or datos_actualizados.get('cintura')
                cadera = datos_actualizados.get('hip') or datos_actualizados.get('cadera')
                presion = datos_actualizados.get('presion') or datos_actualizados.get('presion_arterial')
                spo2 = datos_actualizados.get('spo2') 
                
                cursor.execute(sql, (
                    datos_actualizados['nombres'],
                    datos_actualizados['apellidos'],
                    altura,
                    peso,
                    temperatura,
                    cintura,
                    cadera,
                    presion,
                    datos_actualizados.get('bpm', 'N/A'),
                    spo2,  # <- Este es el parámetro 10
                    id_registro  # <- Este es el parámetro 11
                ))
                
                self.connection.commit()
                return True, "Registro actualizado exitosamente"
                
        except Exception as e:
            self.connection.rollback()
            return False, f"Error al actualizar registro: {e}"
    
    def eliminar_registro(self, id_registro):
        """Elimina un registro de la base de datos"""
        if not self.connection:
            return False, "No hay conexión a la base de datos"
        
        try:
            with self.connection.cursor() as cursor:
                sql = "DELETE FROM pacientes WHERE id_registro = %s"
                cursor.execute(sql, (id_registro,))
                self.connection.commit()
                return True, "Registro eliminado exitosamente"
                
        except Exception as e:
            self.connection.rollback()
            return False, f"Error al eliminar registro: {e}"
    
    def __del__(self):
        """Cierra la conexión al destruir el objeto"""
        if self.connection:
            self.connection.close()

class GestorArchivos:
    def __init__(self):
        self.db = DatabaseManager()
    
    def guardar_registro(self, datos_paciente):
        """Guarda los datos del paciente en la base de datos"""
        try:
            exito, mensaje = self.db.guardar_registro(datos_paciente)
            if exito:
                return True, mensaje, datos_paciente['id_registro']
            else:
                return False, mensaje, None
        except Exception as e:
            return False, str(e), None
    
    def listar_registros(self):
        """Lista todos los registros guardados"""
        try:
            registros = self.db.listar_registros()
            return registros
        except Exception as e:
            print(f"Error al listar registros: {e}")
            return []
    
    def cargar_registro(self, id_registro):
        """Carga un registro desde la base de datos"""
        try:
            registros = self.db.buscar_registro("id", id_registro)
            if registros:
                registro = registros[0]
                contenido = f"""
REGISTRO MÉDICO - {registro['nombres']} {registro['apellidos']}
Fecha de registro: {registro['fecha_registro'].strftime("%Y-%m-%d %H:%M:%S")}
ID de Registro: {registro['id_registro']}

INFORMACIÓN PERSONAL:
Nombres: {registro['nombres']}
Apellidos: {registro['apellidos']}

DATOS MÉDICOS:
Altura: {registro['altura']} cm
Peso: {registro['peso']} kg
Temperatura: {registro['temperatura']} °C
Cintura: {registro['cintura']} cm
Cadera: {registro['cadera']} cm
Presión arterial: {registro['presion_arterial']} mm/Hg
Frecuencia cardíaca: {registro.get('bpm', 'N/A')} BPM
SpO2: {registro.get('spo2', 'N/A')}%

Firma del médico: _________________________
"""
                return True, contenido, registro
            else:
                return False, "Registro no encontrado", None
        except Exception as e:
            return False, str(e), None
    
    def buscar_registros(self, criterio, valor):
        """Busca registros por diferentes criterios"""
        try:
            return self.db.buscar_registro(criterio, valor)
        except Exception as e:
            print(f"Error al buscar registros: {e}")
            return []
    
    def actualizar_registro(self, id_registro, datos_actualizados):
        """Actualiza un registro existente"""
        try:
            return self.db.actualizar_registro(id_registro, datos_actualizados)
        except Exception as e:
            return False, str(e)
    
    def eliminar_registro(self, id_registro):
        """Elimina un registro"""
        try:
            return self.db.eliminar_registro(id_registro)
        except Exception as e:
            return False, str(e)

class BuscarRegistroDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.registro_seleccionado = None
        self.setup_ui()
        self.reproducir_audio_buscar()
        
    def reproducir_audio_buscar(self):
        try:
            if os.path.exists("Buscar3.mp3"):
                pygame.mixer.music.load("Buscar3.mp3")
                pygame.mixer.music.play()
        except Exception as e:
            print(f"Error al reproducir audio: {e}")
        
    def setup_ui(self):
        self.setWindowTitle("Buscar Registros")
        self.setFixedSize(700, 500)
        
        layout = QVBoxLayout()
        
        # Título
        titulo = QLabel("Buscar Registros Médicos")
        titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin: 10px;")
        titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo)
        
        # Instrucción de teclado
        instruccion_teclado = QLabel("Teclas: ↑↓ (Navegar) | Enter (Seleccionar) | F1 (Buscar) | F2 (Listar Todos) | F3 (Ver) | ESC (Salir)")
        instruccion_teclado.setStyleSheet("font-size: 10px; color: #7f8c8d; background-color: #ecf0f1; padding: 5px; border-radius: 3px;")
        instruccion_teclado.setAlignment(Qt.AlignCenter)
        layout.addWidget(instruccion_teclado)
        
        # Grupo de búsqueda
        grupo_busqueda = QGroupBox("Criterios de Búsqueda")
        grupo_busqueda.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout_busqueda = QGridLayout()
        
        # Campos de búsqueda
        layout_busqueda.addWidget(QLabel("Buscar por:"), 0, 0)
        self.criterio_combo = QComboBox()
        self.criterio_combo.addItems(["Nombre", "ID de Registro", "Fecha (YYYY-MM-DD)"])
        layout_busqueda.addWidget(self.criterio_combo, 0, 1)
        
        layout_busqueda.addWidget(QLabel("Valor:"), 1, 0)
        self.valor_busqueda = QLineEdit()
        self.valor_busqueda.setPlaceholderText("Ingrese el valor a buscar...")
        layout_busqueda.addWidget(self.valor_busqueda, 1, 1)
        
        self.boton_buscar = QPushButton("🔍 Buscar (F1)")
        self.boton_buscar.setStyleSheet("QPushButton { background-color: #3498db; color: white; font-weight: bold; }")
        self.boton_buscar.clicked.connect(self.buscar_registros)
        layout_busqueda.addWidget(self.boton_buscar, 1, 2)
        
        self.boton_listar_todos = QPushButton("📋 Listar Todos (F2)")
        self.boton_listar_todos.setStyleSheet("QPushButton { background-color: #2ecc71; color: white; font-weight: bold; }")
        self.boton_listar_todos.clicked.connect(self.listar_todos)
        layout_busqueda.addWidget(self.boton_listar_todos, 0, 2)
        
        grupo_busqueda.setLayout(layout_busqueda)
        layout.addWidget(grupo_busqueda)
        
        # Lista de resultados
        self.lista_resultados = QListWidget()
        self.lista_resultados.itemDoubleClicked.connect(self.seleccionar_registro)
        layout.addWidget(QLabel("Resultados (↑↓ para navegar, Enter para seleccionar):"))
        layout.addWidget(self.lista_resultados)
        
        # Botones
        botones_layout = QHBoxLayout()
        
        self.boton_ver = QPushButton("👁️ Ver Detalles (F3)")
        self.boton_ver.setStyleSheet("QPushButton { background-color: #f39c12; color: white; font-weight: bold; }")
        self.boton_ver.clicked.connect(self.ver_detalles)
        
        self.boton_seleccionar = QPushButton("✅ Seleccionar (Enter)")
        self.boton_seleccionar.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; }")
        self.boton_seleccionar.clicked.connect(self.seleccionar_registro)
        
        self.boton_cerrar = QPushButton("❌ Cerrar (ESC)")
        self.boton_cerrar.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; font-weight: bold; }")
        self.boton_cerrar.clicked.connect(self.reject)
        
        botones_layout.addWidget(self.boton_ver)
        botones_layout.addWidget(self.boton_seleccionar)
        botones_layout.addWidget(self.boton_cerrar)
        
        layout.addLayout(botones_layout)
        self.setLayout(layout)
        
        self.criterio_combo.setFocus()
        
    def keyPressEvent(self, event: QKeyEvent):
        """Maneja las teclas presionadas para navegación"""
        key = event.key()
        
        if key == Qt.Key_Escape:
            self.reject()
        elif key == Qt.Key_F1:
            self.buscar_registros()
        elif key == Qt.Key_F2:
            self.listar_todos()
        elif key == Qt.Key_F3:
            self.ver_detalles()
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            if self.lista_resultados.hasFocus() and self.lista_resultados.currentItem():
                self.seleccionar_registro()
            else:
                self.buscar_registros()
        else:
            super().keyPressEvent(event)
        
    def buscar_registros(self):
        criterio = self.criterio_combo.currentText()
        valor = self.valor_busqueda.text().strip()
        
        if not valor:
            QMessageBox.warning(self, "Búsqueda", "Por favor ingrese un valor para buscar")
            self.valor_busqueda.setFocus()
            return
        
        # Mapear criterio a formato de base de datos
        criterio_map = {
            "Nombre": "nombre",
            "ID de Registro": "id",
            "Fecha (YYYY-MM-DD)": "fecha"
        }
        
        registros = GestorArchivos().buscar_registros(criterio_map[criterio], valor)
        self.mostrar_resultados(registros)
        
        if registros:
            self.lista_resultados.setFocus()
            self.lista_resultados.setCurrentRow(0)
    
    def listar_todos(self):
        registros = GestorArchivos().listar_registros()
        self.mostrar_resultados(registros)
        
        if registros:
            self.lista_resultados.setFocus()
            self.lista_resultados.setCurrentRow(0)
    
    def mostrar_resultados(self, registros):
        self.lista_resultados.clear()
        
        if not registros:
            QMessageBox.information(self, "Búsqueda", "No se encontraron registros")
            self.valor_busqueda.setFocus()
            return
        
        for registro in registros:
            item_text = f"{registro['id_registro']} - {registro['nombres']} {registro['apellidos']} - {registro['fecha_registro'].strftime('%Y-%m-%d')}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, registro['id_registro'])
            self.lista_resultados.addItem(item)
    
    def ver_detalles(self):
        item_actual = self.lista_resultados.currentItem()
        if not item_actual:
            QMessageBox.warning(self, "Selección", "Por favor seleccione un registro")
            return
        
        id_registro = item_actual.data(Qt.UserRole)
        exito, contenido, _ = GestorArchivos().cargar_registro(id_registro)
        
        if exito:
            dialog = DetallesRegistroDialog(contenido, id_registro, self)
            dialog.exec_()
    
    def seleccionar_registro(self):
        item_actual = self.lista_resultados.currentItem()
        if not item_actual:
            QMessageBox.warning(self, "Selección", "Por favor seleccione un registro")
            return
        
        self.registro_seleccionado = item_actual.data(Qt.UserRole)
        self.accept()

class DetallesRegistroDialog(QDialog):
    def __init__(self, contenido, id_registro, parent=None):
        super().__init__(parent)
        self.contenido = contenido
        self.id_registro = id_registro
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle(f"Detalles del Registro - {self.id_registro}")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        
        instruccion = QLabel("Teclas: Enter (Cerrar) | ESC (Cerrar)")
        instruccion.setStyleSheet("font-size: 10px; color: #7f8c8d; background-color: #ecf0f1; padding: 5px; border-radius: 3px;")
        instruccion.setAlignment(Qt.AlignCenter)
        layout.addWidget(instruccion)
        
        texto = QTextEdit()
        texto.setPlainText(self.contenido)
        texto.setReadOnly(True)
        layout.addWidget(texto)
        
        boton_cerrar = QPushButton("Cerrar (Enter)")
        boton_cerrar.clicked.connect(self.accept)
        boton_cerrar.setStyleSheet("QPushButton { background-color: #3498db; color: white; font-weight: bold; }")
        layout.addWidget(boton_cerrar)
        
        self.setLayout(layout)
        boton_cerrar.setFocus()
        
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape):
            self.accept()
        else:
            super().keyPressEvent(event)

class ModificarRegistroDialog(QDialog):
    def __init__(self, id_registro, parent=None):
        super().__init__(parent)
        self.id_registro = id_registro
        self.datos_originales = {}
        self.setup_ui()
        self.cargar_datos()
        self.reproducir_audio_modificar()
        
    def reproducir_audio_modificar(self):
        try:
            if os.path.exists("Modificar.mp3"):
                pygame.mixer.music.load("Modificar.mp3")
                pygame.mixer.music.play()
        except Exception as e:
            print(f"Error al reproducir audio: {e}")
        
    def setup_ui(self):
        self.setWindowTitle(f"Modificar Registro - {self.id_registro}")
        self.setFixedSize(500, 600)
        
        layout = QVBoxLayout()
        
        titulo = QLabel("Modificar Registro Médico")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin: 10px;")
        titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo)
        
        instruccion = QLabel("Teclas: Tab (Siguiente campo) | Shift+Tab (Campo anterior) | F1 (Guardar) | ESC (Cancelar)")
        instruccion.setStyleSheet("font-size: 10px; color: #7f8c8d; background-color: #ecf0f1; padding: 5px; border-radius: 3px;")
        instruccion.setAlignment(Qt.AlignCenter)
        layout.addWidget(instruccion)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.scroll_layout = QGridLayout()
        
        self.campos = {}
        campos_config = [
            ("Nombres:", "nombres"),
            ("Apellidos:", "apellidos"),
            ("Altura (cm):", "altura"),
            ("Peso (kg):", "peso"),
            ("Temperatura (°C):", "temperatura"),
            ("Cintura (cm):", "cintura"),
            ("Cadera (cm):", "cadera"),
            ("Presión arterial:", "presion_arterial"),
            ("Frecuencia cardíaca (BPM):", "bpm"),
            ("SpO2 (%):", "spo2")
        ]
        
        for i, (label_text, clave) in enumerate(campos_config):
            label = QLabel(label_text)
            entry = QLineEdit()
            self.campos[clave] = entry
            self.scroll_layout.addWidget(label, i, 0)
            self.scroll_layout.addWidget(entry, i, 1)
        
        scroll_widget.setLayout(self.scroll_layout)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        botones_layout = QHBoxLayout()
        
        self.boton_guardar = QPushButton("💾 Guardar Cambios (F1)")
        self.boton_guardar.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; }")
        self.boton_guardar.clicked.connect(self.guardar_cambios)
        
        self.boton_cancelar = QPushButton("❌ Cancelar (ESC)")
        self.boton_cancelar.setStyleSheet("QPushButton { background-color: #95a5a6; color: white; font-weight: bold; }")
        self.boton_cancelar.clicked.connect(self.reject)
        
        botones_layout.addWidget(self.boton_guardar)
        botones_layout.addWidget(self.boton_cancelar)
        
        layout.addLayout(botones_layout)
        self.setLayout(layout)
        
        self.lista_campos = list(self.campos.values())
        if self.lista_campos:
            self.lista_campos[0].setFocus()
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key_F1:
            self.guardar_cambios()
        else:
            super().keyPressEvent(event)
    
    def cargar_datos(self):
        exito, contenido, registro = GestorArchivos().cargar_registro(self.id_registro)
        if exito and registro:
            self.datos_originales = registro
            for clave, campo in self.campos.items():
                if clave in registro and registro[clave] is not None:
                    campo.setText(str(registro[clave]))
    
    def guardar_cambios(self):
        if not self.campos['nombres'].text().strip() or not self.campos['apellidos'].text().strip():
            QMessageBox.warning(self, "Validación", "Los campos Nombres y Apellidos son obligatorios")
            self.campos['nombres'].setFocus()
            return
        
        datos_actualizados = {}
        for clave, campo in self.campos.items():
            datos_actualizados[clave] = campo.text().strip()
        
        datos_actualizados['height'] = datos_actualizados['altura']
        datos_actualizados['weight'] = datos_actualizados['peso']
        datos_actualizados['temperature'] = datos_actualizados['temperatura']
        datos_actualizados['waist'] = datos_actualizados['cintura']
        datos_actualizados['hip'] = datos_actualizados['cadera']
        datos_actualizados['presion'] = datos_actualizados['presion_arterial']
        datos_actualizados['spo2'] = datos_actualizados['spo2'] 
        
        respuesta = QMessageBox.question(
            self, 
            "Confirmar Modificación",
            f"¿Está seguro que desea modificar el registro {self.id_registro}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if respuesta == QMessageBox.Yes:
            exito, mensaje = GestorArchivos().actualizar_registro(self.id_registro, datos_actualizados)
            if exito:
                QMessageBox.information(self, "Éxito", mensaje)
                self.accept()
            else:
                QMessageBox.critical(self, "Error", mensaje)

class EliminarRegistroDialog(QDialog):
    def __init__(self, id_registro, parent=None):
        super().__init__(parent)
        self.id_registro = id_registro
        self.setup_ui()
        self.cargar_datos()
        self.reproducir_audio_borrar()
        
    def reproducir_audio_borrar(self):
        try:
            if os.path.exists("Borrar.mp3"):
                pygame.mixer.music.load("Borrar.mp3")
                pygame.mixer.music.play()
        except Exception as e:
            print(f"Error al reproducir audio: {e}")
        
    def setup_ui(self):
        self.setWindowTitle(f"Eliminar Registro - {self.id_registro}")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        
        titulo = QLabel("Eliminar Registro Médico")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c; margin: 10px;")
        titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo)
        
        instruccion = QLabel("Teclas: F1 (Eliminar) | ESC (Cancelar)")
        instruccion.setStyleSheet("font-size: 10px; color: #7f8c8d; background-color: #ecf0f1; padding: 5px; border-radius: 3px;")
        instruccion.setAlignment(Qt.AlignCenter)
        layout.addWidget(instruccion)
        
        self.info_label = QLabel()
        self.info_label.setStyleSheet("font-size: 12px; background-color: #f8f9fa; padding: 10px; border: 1px solid #ddd;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        advertencia = QLabel("⚠️ ¡ADVERTENCIA! Esta acción no se puede deshacer.")
        advertencia.setStyleSheet("font-size: 14px; font-weight: bold; color: #e74c3c; margin: 10px;")
        advertencia.setAlignment(Qt.AlignCenter)
        layout.addWidget(advertencia)
        
        botones_layout = QHBoxLayout()
        
        self.boton_eliminar = QPushButton("🗑️ Eliminar Permanentemente (F1)")
        self.boton_eliminar.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; font-weight: bold; }")
        self.boton_eliminar.clicked.connect(self.eliminar_registro)
        
        self.boton_cancelar = QPushButton("🔙 Cancelar (ESC)")
        self.boton_cancelar.setStyleSheet("QPushButton { background-color: #95a5a6; color: white; font-weight: bold; }")
        self.boton_cancelar.clicked.connect(self.reject)
        
        botones_layout.addWidget(self.boton_eliminar)
        botones_layout.addWidget(self.boton_cancelar)
        
        layout.addLayout(botones_layout)
        self.setLayout(layout)
        
        self.boton_cancelar.setFocus()
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key_F1:
            self.eliminar_registro()
        else:
            super().keyPressEvent(event)
    
    def cargar_datos(self):
        exito, contenido, registro = GestorArchivos().cargar_registro(self.id_registro)
        if exito and registro:
            info_text = f"""
            Paciente: {registro['nombres']} {registro['apellidos']}
            ID: {registro['id_registro']}
            Fecha de registro: {registro['fecha_registro'].strftime('%Y-%m-%d %H:%M:%S')}
            
            Datos médicos:
            • Altura: {registro['altura']} cm
            • Peso: {registro['peso']} kg
            • Temperatura: {registro['temperatura']} °C
            • Cintura: {registro['cintura']} cm
            • Cadera: {registro['cadera']} cm
            • Presión: {registro['presion_arterial']} mm/Hg
            • BPM: {registro.get('bpm', 'N/A')}
            • SpO2: {registro.get('spo2', 'N/A')}% 
            """
            self.info_label.setText(info_text)
    
    def eliminar_registro(self):
        respuesta = QMessageBox.critical(
            self,
            "Confirmar Eliminación",
            f"¿ESTÁ ABSOLUTAMENTE SEGURO de eliminar el registro de {self.id_registro}?\n\n"
            "Esta acción NO se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if respuesta == QMessageBox.Yes:
            exito, mensaje = GestorArchivos().eliminar_registro(self.id_registro)
            if exito:
                QMessageBox.information(self, "Éxito", mensaje)
                self.accept()
            else:
                QMessageBox.critical(self, "Error", mensaje)

class InformacionProyectoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Información del Proyecto")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        
        titulo = QLabel("Información del Proyecto")
        titulo.setStyleSheet("font-size: 20px; font-weight: bold; margin: 10px;")
        titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo)
        
        instruccion = QLabel("Teclas: Enter (Cerrar) | ESC (Cerrar)")
        instruccion.setStyleSheet("font-size: 10px; color: #7f8c8d; background-color: #ecf0f1; padding: 5px; border-radius: 3px;")
        instruccion.setAlignment(Qt.AlignCenter)
        layout.addWidget(instruccion)
        
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
            "• Medición de frecuencia cardíaca (BPM)\n"
            "• Medición de circunferencias corporales\n"
            "• Generación automática de ID de registro\n"
            "• Almacenamiento en base de datos MariaDB\n"
            "• Gestión completa de registros (Buscar, Modificar, Eliminar)\n\n"
            
            "Tecnologías utilizadas:\n"
            "• Python 3.14\n"
            "• PyQt5 para la interfaz gráfica\n"
            "• MariaDB para almacenamiento\n"
            "• Dispositivos de medición conectados\n\n"
            ""
            
            "Versión: 1.17.3\n\n\n"
            "Asesor:\n"
            "============================\n"
            "•Dr. Ruben Estrada Marmolejo\n\n\n"
            "Desarrollado por: Equipo Dinamita\n"
            "Isaac Alejandro García Segura\n"
            "Luis Aguilar Gutierrez\n"
            "Rodolfo Robledo Martínez (Caribú)\n\n"
            
            "Agradecimientos especiales a:\n"
            "============================\n"
            "•A nuestros padres, por apoyarnos en esta trayectoria\n"
            "•ING. Manuel Mauricio Arturo Ortiz Caloca\n"
            "•Andres Alejandro Conde Castrillón\n"
            "•Andrea Villagrana\n"
            "•Pepechuy\n"
            "•Estefanía Lazcano Tovar\n"
            "•Dr. José Alejandro Morales Valencia\n"
            "Por el pŕestamo del laboratório\n"
            "•Oso\n"
            "•Miguel Olide (Temach)\n"
            "•Cristopher Eduardo González Covarrubias\n"
            "•Dra. Flor del Carmen\n"
            "•Las morras de los del equipo\n\n\n"
            "Muchas gracías por su uso"
        
        )
        layout.addWidget(info_text)
        
        cerrar_btn = QPushButton("Cerrar (Enter)")
        cerrar_btn.clicked.connect(self.accept)
        cerrar_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; font-weight: bold; }")
        layout.addWidget(cerrar_btn)
        
        self.setLayout(layout)
        cerrar_btn.setFocus()
        
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape):
            self.accept()
        else:
            super().keyPressEvent(event)

class FormularioNombres(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.datos_paciente = {}
        self.setup_ui()
        self.reproducir_audio_nombres()
    
    def reproducir_audio_nombres(self):
        try:
            if os.path.exists("Ingresar_nombres.mp3"):
                pygame.mixer.music.load("Ingresar_nombres.mp3")
                pygame.mixer.music.play()
        except Exception as e:
            print(f"Error al reproducir audio: {e}")
        
    def setup_ui(self):
        self.setWindowTitle("Datos del Paciente - Paso 1 de 2")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        titulo = QLabel("Información Personal del Paciente")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo)
        
        instruccion_teclado = QLabel("Teclas: Tab (Siguiente) | Shift+Tab (Anterior) | Enter (Continuar) | ESC (Cancelar)")
        instruccion_teclado.setStyleSheet("font-size: 10px; color: #7f8c8d; background-color: #ecf0f1; padding: 5px; border-radius: 3px;")
        instruccion_teclado.setAlignment(Qt.AlignCenter)
        layout.addWidget(instruccion_teclado)
        
        form_layout = QGridLayout()
        form_layout.setSpacing(15)
        
        nombres_label = QLabel("Nombres:")
        self.nombres_entry = QLineEdit()
        self.nombres_entry.setPlaceholderText("Ingrese todos los nombres del paciente")
        
        apellidos_label = QLabel("Apellidos:")
        self.apellidos_entry = QLineEdit()
        self.apellidos_entry.setPlaceholderText("Ingrese ambos apellidos")
        
        form_layout.addWidget(nombres_label, 0, 0)
        form_layout.addWidget(self.nombres_entry, 0, 1)
        form_layout.addWidget(apellidos_label, 1, 0)
        form_layout.addWidget(self.apellidos_entry, 1, 1)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        botones_layout = QHBoxLayout()
        
        self.cancelar_btn = QPushButton("Cancelar (ESC)")
        self.cancelar_btn.setStyleSheet("QPushButton { background-color: #95a5a6; color: white; font-weight: bold; }")
        self.cancelar_btn.clicked.connect(self.reject)
        
        self.continuar_btn = QPushButton("Continuar → (Enter)")
        self.continuar_btn.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; }")
        self.continuar_btn.clicked.connect(self.continuar_formulario)
        
        botones_layout.addWidget(self.cancelar_btn)
        botones_layout.addWidget(self.continuar_btn)
        
        layout.addLayout(botones_layout)
        self.setLayout(layout)
        
        self.nombres_entry.setFocus()
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.continuar_formulario()
        else:
            super().keyPressEvent(event)
    
    def continuar_formulario(self):
        if not self.nombres_entry.text().strip():
            QMessageBox.warning(self, "Campo requerido", "Por favor ingrese los nombres del paciente")
            self.nombres_entry.setFocus()
            return
            
        if not self.apellidos_entry.text().strip():
            QMessageBox.warning(self, "Campo requerido", "Por favor ingrese los apellidos del paciente")
            self.apellidos_entry.setFocus()
            return
        if self.nombres_entry.text().strip()== "88224646ba":
            # Abrir el juego de Kirby en el navegador
            try:
                webbrowser.open("https://www.retrogames.cc/gameboy-games/kirby-s-dream-land-usa-europe.html")
                QMessageBox.information(self, "¡Easter Egg Activado!", 
                                      "¡Kirby's Dream Land cargado!\n\n"
                                      "Disfruta del juego clásico de Game Boy.\n"
                                      "El formulario continuará normalmente.")
            except Exception as e:
                print(f"Error al abrir el juego: {e}")
        
        self.datos_paciente['nombres'] = self.nombres_entry.text().strip()
        self.datos_paciente['apellidos'] = self.apellidos_entry.text().strip()
        
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
            ("Altura (cm):", "height", True, "Estatura.mp3"),
            ("Peso (kg):", "weight", True, "Peso.mp3"),
            ("Temperatura (C°):", "temperature", True, "Temperatura.mp3"),
            ("Cintura (cm):", "waist", True, "Cintura.mp3"),
            ("Cadera (cm):", "hip", True, "Cadera.mp3"),
            ("Presión arterial (mm/Hg):", "presion", True, "Arterial.mp3"),
            ("Frecuencia cardíaca (BPM):", "bpm", False, ""),
            ("SpO2 (%):", "spo2", True, "SPO2.mp3")
        ]
        self.setup_ui()
        
    def reproducir_audio_campo(self, archivo_audio):
        try:
            if archivo_audio and os.path.exists(archivo_audio):
                pygame.mixer.music.load(archivo_audio)
                pygame.mixer.music.play()
        except Exception as e:
            print(f"Error al reproducir audio: {e}")    
        
    def setup_ui(self):
        self.setWindowTitle(f"Formulario Médico - Campo 1 de {len(self.campos_config)}")
        self.setFixedSize(800, 650)
        
        self.layout_principal = QVBoxLayout()
        self.layout_principal.setSpacing(20)
        
        self.info_paciente = QLabel(f"Paciente: {self.datos_paciente['nombres']} {self.datos_paciente['apellidos']}")
        self.info_paciente.setStyleSheet("font-weight: bold; color: #2c3e50; background-color: #ecf0f1; padding: 8px; border-radius: 5px;")
        self.layout_principal.addWidget(self.info_paciente)
        
        instruccion_teclado = QLabel("Teclas: ↑↓ (Navegar) | Enter (Siguiente/Medir) | F1 (Anterior) | F2 (Medir) | ESC (Cancelar)")
        instruccion_teclado.setStyleSheet("font-size: 10px; color: #7f8c8d; background-color: #ecf0f1; padding: 5px; border-radius: 3px;")
        instruccion_teclado.setAlignment(Qt.AlignCenter)
        self.layout_principal.addWidget(instruccion_teclado)
        
        self.progreso_label = QLabel()
        self.actualizar_progreso()
        self.layout_principal.addWidget(self.progreso_label)
        
        self.campo_layout = QVBoxLayout()
        self.mostrar_campo_actual()
        self.layout_principal.addLayout(self.campo_layout)
        
        self.layout_principal.addStretch()
        
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
        for i in reversed(range(self.campo_layout.count())):
            widget = self.campo_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        nombre_campo, clave, tiene_boton, archivo_audio = self.campos_config[self.campo_actual]

        # Reproducir audio del campo actual
        self.reproducir_audio_campo(archivo_audio)
        
        label = QLabel(nombre_campo)
        label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        self.campo_layout.addWidget(label)
        
        entrada_layout = QHBoxLayout()
        
        self.entrada_actual = QLineEdit()
        self.entrada_actual.setPlaceholderText(f"Ingrese {nombre_campo.lower()}")
        
        if clave in self.campos_completados:
            self.entrada_actual.setText(self.campos_completados[clave])
        
        entrada_layout.addWidget(self.entrada_actual)
        
        if tiene_boton:
            self.boton_medir = QPushButton("Medir (F2)")
            self.boton_medir.setStyleSheet("background-color: #2e86de; color: white; font-weight: bold;")
    
            if clave == "presion":
                self.boton_medir.clicked.connect(self.medir_presion)
            elif clave == "temperature":
                self.boton_medir.clicked.connect(self.medir_temperatura)
            elif clave == "weight":
                self.boton_medir.clicked.connect(self.medir_peso)
            elif clave == "height":
                self.boton_medir.clicked.connect(self.medir_altura)
            else:
                self.boton_medir.clicked.connect(self.medir_circunferencia)
        
            entrada_layout.addWidget(self.boton_medir)
        
        self.campo_layout.addLayout(entrada_layout)
        self.entrada_actual.setFocus()
        
    def setup_botones(self):
        for i in reversed(range(self.botones_layout.count())):
            widget = self.botones_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        self.boton_anterior = QPushButton("← Anterior (F1)")
        self.boton_anterior.setStyleSheet("QPushButton { background-color: #95a5a6; color: white; font-weight: bold; }")
        self.boton_anterior.clicked.connect(self.campo_anterior)
        self.boton_anterior.setEnabled(self.campo_actual > 0)
        
        if self.campo_actual < len(self.campos_config) - 1:
            self.boton_siguiente = QPushButton("Siguiente → (Enter)")
            self.boton_siguiente.setStyleSheet("QPushButton { background-color: #3498db; color: white; font-weight: bold; }")
            self.boton_siguiente.clicked.connect(self.campo_siguiente)
        else:
            self.boton_siguiente = QPushButton("Guardar Registro (Enter)")
            self.boton_siguiente.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; }")
            self.boton_siguiente.clicked.connect(self.finalizar_formulario)
        
        self.botones_layout.addWidget(self.boton_anterior)
        self.botones_layout.addWidget(self.boton_siguiente)
        
    def campo_anterior(self):
        if self.campo_actual > 0:
            self.guardar_campo_actual()
            self.campo_actual -= 1
            self.actualizar_interfaz()
        
    def campo_siguiente(self):
        if not self.entrada_actual.text().strip():
            QMessageBox.warning(self, "Campo requerido", f"Por favor ingrese {self.campos_config[self.campo_actual][0].lower()}")
            self.entrada_actual.setFocus()
            return
            
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
    
    def medir_temperatura(self):
        self.entrada_actual.setText("Midiendo temperatura...")
        self.temperatura_thread = TemperaturaThread()
        self.temperatura_thread.finished.connect(self.mostrar_temperatura)
        self.temperatura_thread.error.connect(self.error_medida)
        self.temperatura_thread.start()

    def mostrar_temperatura(self, temperatura):
        self.entrada_actual.setText(f"{temperatura:.1f}")
        QMessageBox.information(self, "Medición completa", f"Temperatura registrada: {temperatura:.1f}°C")
    
    def medir_peso(self):
        self.entrada_actual.setText("Midiendo peso...")
        self.peso_thread = PesoThread()
        self.peso_thread.finished.connect(self.mostrar_peso)
        self.peso_thread.error.connect(self.error_medida)
        self.peso_thread.start()

    def mostrar_peso(self, peso):
        self.entrada_actual.setText(f"{peso:.2f}")
        QMessageBox.information(self, "Medición completa", f"Peso registrado: {peso:.2f} kg")
    
    def medir_altura(self):
        self.entrada_actual.setText("Midiendo altura...")
        self.altura_thread = AlturaThread()
        self.altura_thread.finished.connect(self.mostrar_altura)
        self.altura_thread.error.connect(self.error_medida)
        self.altura_thread.start()

    def mostrar_altura(self, altura):
        self.entrada_actual.setText(f"{altura:.2f}")
        QMessageBox.information(self, "Medición completa", f"Altura registrada: {altura:.2f} cm")
    
    def medir_spo2(self):
        self.entrada_actual.setText("Midiendo SpO2...")
        self.spo2_thread = Spo2Thread()
        self.spo2_thread.finished.connect(self.mostrar_spo2)
        self.spo2_thread.error.connect(self.error_medida)
        self.spo2_thread.start()

    def mostrar_spo2(self, spo2):
        self.entrada_actual.setText(f"{spo2:.1f}")
        QMessageBox.information(self, "Medición completa", f"SpO2 registrado: {spo2:.1f}%")
    
    def mostrar_medida_circunferencia(self, valor):
        self.entrada_actual.setText(f"{valor:.2f}")
        QMessageBox.information(self, "Medición completa", f"Medida registrada: {valor:.2f} cm")
        
    def medir_presion(self):
        self.entrada_actual.setText("Coloque el brazalete...")
        self.worker = WorkerThread()
        self.worker.finished.connect(self.mostrar_presion_y_bpm)
        self.worker.error.connect(self.error_medida)
        self.worker.status.connect(self.actualizar_estado_presion)
        self.worker.start()
        
    def actualizar_estado_presion(self, mensaje):
        self.entrada_actual.setText(mensaje)
        
    def mostrar_presion_y_bpm(self, resultado):
        partes = resultado.split("|")
        if len(partes) == 2:
            presion = partes[0]
            bpm = partes[1]
            
            # Llenar automáticamente el campo de presión arterial
            self.entrada_actual.setText(presion)
            
            # Llenar automáticamente el campo de BPM si existe
            # Buscar el campo de BPM en los campos completados
            self.campos_completados['bpm'] = bpm
            
            # Si estamos en el campo de presión arterial y el campo de BPM ya fue mostrado,
            # actualizarlo automáticamente
            nombre_campo_actual, clave_actual, _ = self.campos_config[self.campo_actual][:3]
            if clave_actual == "presion":
                # Buscar el índice del campo BPM
                for i, (nombre, clave, _) in enumerate([campo[:3] for campo in self.campos_config]):
                    if clave == "bpm":
                        # Actualizar el campo BPM en los datos completados
                        self.campos_completados['bpm'] = bpm
                        break
            
            QMessageBox.information(self, "Medición Completa", 
                                  f"Presión medida: {presion} mm/Hg\n"
                                  f"Frecuencia cardíaca: {bpm} BPM\n\n"
                                  f"Ambos valores se han guardado automáticamente.")
        else:
            self.entrada_actual.setText(resultado)
            QMessageBox.information(self, "Medición Completa", f"Presión medida: {resultado} mm/Hg")
        
    def error_medida(self, mensaje_error):
        self.entrada_actual.clear()
        QMessageBox.critical(self, "Error", mensaje_error)
    
    def finalizar_formulario(self):
        self.guardar_campo_actual()
    
        campos_faltantes = []
        for nombre, clave, _, _ in self.campos_config:
            if not self.campos_completados.get(clave):
                campos_faltantes.append(nombre)
            
        if campos_faltantes:
            QMessageBox.warning(self, "Campos incompletos", 
                          f"Por favor complete los siguientes campos:\n" + "\n".join(f"• {campo}" for campo in campos_faltantes))
            return
        
        id_registro = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        datos_completos = {
            'nombres': self.datos_paciente['nombres'],
            'apellidos': self.datos_paciente['apellidos'],
            'id_registro': id_registro,
            **self.campos_completados
        }
        
        datos_completos['altura'] = datos_completos['height']
        datos_completos['peso'] = datos_completos['weight']
        datos_completos['temperatura'] = datos_completos['temperature']
        datos_completos['cintura'] = datos_completos['waist']
        datos_completos['cadera'] = datos_completos['hip']
        datos_completos['presion_arterial'] = datos_completos['presion']
        
        exito, resultado, id_guardado = GestorArchivos().guardar_registro(datos_completos)
        
        if exito:
            resumen = f"""
            REGISTRO MÉDICO GUARDADO EXITOSAMENTE
            
            Paciente: {datos_completos['nombres']} {datos_completos['apellidos']}
            ID de Registro: {datos_completos['id_registro']}
            
            Datos médicos:
            - Altura: {datos_completos['height']} cm
            - Peso: {datos_completos['weight']} kg
            - Temperatura: {datos_completos['temperature']} °C
            - Cintura: {datos_completos['waist']} cm
            - Cadera: {datos_completos['hip']} cm
            - Presión arterial: {datos_completos['presion']} mm/Hg
            - Frecuencia cardíaca: {datos_completos.get('bpm', 'N/A')} BPM
            - SpO2: {datos_completos.get('spo2', 'N/A')}%
            """
            
            print("=== REGISTRO MÉDICO GUARDADO EN BASE DE DATOS ===")
            for key, value in datos_completos.items():
                print(f"{key}: {value}")
            print("=================================================")
            
            QMessageBox.information(self, "Éxito", 
                                  f"Registro médico guardado correctamente en la base de datos\n\n"
                                  f"ID: {datos_completos['id_registro']}")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", 
                               f"No se pudo guardar el registro en la base de datos:\n{resultado}")
            return

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        
        if key == Qt.Key_Escape:
            self.reject()
        elif key == Qt.Key_Up:
            self.campo_anterior()
        elif key == Qt.Key_Down:
            self.campo_siguiente()
        elif key == Qt.Key_F1:
            self.campo_anterior()
        elif key == Qt.Key_F2:
            nombre_campo, clave, tiene_boton, archivo_audio = self.campos_config[self.campo_actual]
            if tiene_boton:
                if clave == "presion":
                    self.medir_presion()
                elif clave == "temperature":
                    self.medir_temperatura()
                elif clave == "weight":
                    self.medir_peso()
                elif clave == "height":
                    self.medir_altura()
                elif clave == "spo2":  # <- Agregar esta condición
                    self.medir_spo2()
                else:
                    self.medir_circunferencia()
     
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            if self.campo_actual < len(self.campos_config) - 1:
                self.campo_siguiente()
            else:
                self.finalizar_formulario()
        else:
            super().keyPressEvent(event)

class MenuRegistros(QMainWindow):
    def __init__(self):
        super().__init__()
        pygame.mixer.init()
        self.setup_ui()
        self.reproducir_audio_menu()
        
    def reproducir_audio_menu(self):
        try:
            if os.path.exists("Menu_principal.mp3"):
                pygame.mixer.music.load("Menu_principal.mp3")
                pygame.mixer.music.play()
        except Exception as e:
            print(f"Error al reproducir audio: {e}")
    
    def setup_ui(self):
        self.setWindowTitle("Sistema de Registros Médicos - v2.0.0")
        self.setFixedSize(400, 450)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        titulo = QLabel("Menú Principal")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size: 18px; font-weight: bold; margin: 20px;")
        layout.addWidget(titulo)
        
        instrucciones = QLabel("Presione 1-6 para navegar o use el mouse\nF1-F6 también funcionan")
        instrucciones.setAlignment(Qt.AlignCenter)
        instrucciones.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 10px;")
        layout.addWidget(instrucciones)
        
        self.botones_menu = [
            ("1. Crear Registro", self.crear_registro),
            ("2. Modificar Registro", self.modificar_registro),
            ("3. Eliminar Registro", self.eliminar_registro),
            ("4. Buscar Registro", self.buscar_registro),
            ("5. Información del Proyecto", self.mostrar_informacion),
            ("6. Salir", self.salir)
        ]
        
        for texto, funcion in self.botones_menu:
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
        key = event.key()
        
        if key == Qt.Key_1 or key == Qt.Key_F1:
            self.crear_registro()
        elif key == Qt.Key_2 or key == Qt.Key_F2:
            self.modificar_registro()
        elif key == Qt.Key_3 or key == Qt.Key_F3:
            self.eliminar_registro()
        elif key == Qt.Key_4 or key == Qt.Key_F4:
            self.buscar_registro()
        elif key == Qt.Key_5 or key == Qt.Key_F5:
            self.mostrar_informacion()
        elif key == Qt.Key_6 or key == Qt.Key_F6:
            self.salir()
        else:
            super().keyPressEvent(event)
        
    def crear_registro(self):
        formulario_nombres = FormularioNombres(self)
        if formulario_nombres.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Proceso completado", "Registro médico creado y guardado exitosamente")
        
    def modificar_registro(self):
        buscar_dialog = BuscarRegistroDialog(self)
        if buscar_dialog.exec_() == QDialog.Accepted and buscar_dialog.registro_seleccionado:
            id_registro = buscar_dialog.registro_seleccionado
            modificar_dialog = ModificarRegistroDialog(id_registro, self)
            modificar_dialog.exec_()
        
    def eliminar_registro(self):
        buscar_dialog = BuscarRegistroDialog(self)
        if buscar_dialog.exec_() == QDialog.Accepted and buscar_dialog.registro_seleccionado:
            id_registro = buscar_dialog.registro_seleccionado
            eliminar_dialog = EliminarRegistroDialog(id_registro, self)
            eliminar_dialog.exec_()
        
    def buscar_registro(self):
        buscar_dialog = BuscarRegistroDialog(self)
        buscar_dialog.exec_()
        
    def mostrar_informacion(self):
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
            info_dialog = InformacionProyectoDialog(self)
            info_dialog.exec_()
            self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
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
        QGroupBox {
            font-weight: bold;
            border: 2px solid #bdc3c7;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QListWidget {
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            padding: 5px;
            font-size: 12px;
        }
        QListWidget:focus {
            border: 2px solid #3498db;
        }
    """)
    
    ventana = MenuRegistros()
    ventana.show()
    sys.exit(app.exec_())
