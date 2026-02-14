"""
Sistema de gestión de proyectos
跟踪 tus proyectos con memoria, status y próximos pasos
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Optional

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_FILE = os.path.join(CURRENT_DIR, '..', 'data', 'proyectos.json')


class GestorProyectos:
    """Gestor de proyectos personales"""
    
    def __init__(self):
        self.proyectos = self._cargar()
    
    def _cargar(self) -> Dict:
        """Carga los proyectos desde archivo"""
        if os.path.exists(PROJECTS_FILE):
            try:
                with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _guardar(self):
        """Guarda los proyectos a archivo"""
        os.makedirs(os.path.dirname(PROJECTS_FILE), exist_ok=True)
        with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.proyectos, f, indent=2, ensure_ascii=False)
    
    def agregar(self, nombre: str, descripcion: str = "", estado: str = "activo", tags: List[str] = None) -> str:
        """Agrega un nuevo proyecto"""
        if nombre.lower() in self.proyectos:
            return f"⚠️ El proyecto '{nombre}' ya existe"
        
        self.proyectos[nombre.lower()] = {
            'nombre': nombre,
            'descripcion': descripcion,
            'estado': estado,  # activo, pausado, completado
            'tags': tags or [],
            'creado': datetime.now().strftime("%Y-%m-%d"),
            'actualizado': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'notas': []
        }
        self._guardar()
        return f"✅ Proyecto '{nombre}' creado"
    
    def actualizar(self, nombre: str, **kwargs) -> str:
        """Actualiza un proyecto"""
        nombre = nombre.lower()
        if nombre not in self.proyectos:
            return f"⚠️ Proyecto '{nombre}' no encontrado"
        
        for key, value in kwargs.items():
            if key in self.proyectos[nombre]:
                self.proyectos[nombre][key] = value
        
        self.proyectos[nombre]['actualizado'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._guardar()
        return f"✅ Proyecto '{nombre}' actualizado"
    
    def agregar_nota(self, nombre: str, nota: str) -> str:
        """Agrega una nota al proyecto"""
        nombre = nombre.lower()
        if nombre not in self.proyectos:
            return f"⚠️ Proyecto '{nombre}' no encontrado"
        
        self.proyectos[nombre]['notas'].append({
            'fecha': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'nota': nota
        })
        self.proyectos[nombre]['actualizado'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._guardar()
        return f"✅ Nota agregada a '{nombre}'"
    
    def listar(self, filtro: str = None) -> str:
        """Lista todos los proyectos"""
        if not self.proyectos:
            return "📋 No hay proyectos todavía"
        
        if filtro:
            filtrados = {k: v for k, v in self.proyectos.items() 
                        if filtro.lower() in k or filtro.lower() in (v.get('estado', '') or '')}
        else:
            filtrados = self.proyectos
        
        if not filtrados:
            return f"📋 No hay proyectos con '{filtro}'"
        
        msg = "📋 *Proyectos*\n\n"
        
        # Agrupar por estado
        por_estado = {'activo': [], 'pausado': [], 'completado': []}
        for nombre, data in filtrados.items():
            estado = data.get('estado', 'activo')
            if estado not in por_estado:
                por_estado[estado] = []
            por_estado[estado].append((nombre, data))
        
        for estado in ['activo', 'pausado', 'completado']:
            if por_estado[estado]:
                emoji = {'activo': '🟢', 'pausado': '🟡', 'completado': '✅'}.get(estado, '⚪')
                msg += f"*{emoji} {estado.upper()}*\n"
                for nombre, data in por_estado[estado]:
                    nombre_mostrar = data.get('nombre', nombre)
                    actualizado = data.get('actualizado', '')
                    msg += f"• {nombre_mostrar} (upd: {actualizado[:10]})\n"
                msg += "\n"
        
        return msg
    
    def status(self, nombre: str = None) -> str:
        """Muestra el status de un proyecto o todos"""
        if nombre:
            nombre = nombre.lower()
            if nombre not in self.proyectos:
                return f"⚠️ Proyecto '{nombre}' no encontrado"
            
            data = self.proyectos[nombre]
            msg = f"""📊 *{data.get('nombre', nombre)}*

*Estado:* {data.get('estado', 'activo')}
*Creado:* {data.get('creado', '?')}
*Actualizado:* {data.get('actualizado', '?')}

*Descripción:* {data.get('descripcion', 'Sin descripción')}

*Etiquetas:* {', '.join(data.get('tags', [])) or 'Sin etiquetas'}
"""
            if data.get('notas'):
                msg += "*Notas Recientes:*\n"
                for nota in data['notas'][-5:]:
                    msg += f"• [{nota['fecha'][:10]}] {nota['nota']}\n"
            
            return msg
        else:
            return self.listar()
    
    def proximo(self, nombre: str = None) -> str:
        """Muestra el próximo paso de un proyecto"""
        if nombre:
            nombre = nombre.lower()
            if nombre not in self.proyectos:
                return f"⚠️ Proyecto '{nombre}' no encontrado"
            
            data = self.proyectos[nombre]
            if data.get('notas'):
                ultima = data['notas'][-1]
                return f"📌 *Próximo paso para {data.get('nombre', nombre)}:*\n\n{ultima['nota']}"
            else:
                return f"📌 No hay notas en '{nombre}'"
        else:
            # Devolver el proyecto activo más reciente
            activos = [(k, v) for k, v in self.proyectos.items() if v.get('estado') == 'activo']
            if activos:
                activos.sort(key=lambda x: x[1].get('actualizado', ''), reverse=True)
                nombre, data = activos[0]
                if data.get('notas'):
                    return f"📌 *Próximo paso ({data.get('nombre', nombre)}):*\n\n{data['notas'][-1]['nota']}"
            return "📌 No hay proyectos activos"


# Instancia global
gestor = GestorProyectos()


# Funciones helper para comandos
def cmd_proyectos(args: List[str]) -> str:
    """Maneja el comando /proyectos"""
    if not args:
        return gestor.listar()
    
    subcmd = args[0].lower()
    
    if subcmd == 'list' or subcmd == 'lista':
        return gestor.listar(args[1] if len(args) > 1 else None)
    
    elif subcmd == 'add' or subcmd == 'agregar':
        # /proyectos add Nombre - descripcion - tag1,tag2
        if len(args) < 2:
            return "⚠️ Uso: /proyectos add Nombre - descripción - tag1,tag2"
        
        nombre = args[1]
        descripcion = ""
        tags = []
        
        if len(args) > 2:
            partes = ' '.join(args[2:]).split(' - ')
            if len(partes) > 0:
                descripcion = partes[0].strip()
            if len(partes) > 1:
                tags = [t.strip() for t in partes[1].split(',') if t.strip()]
        
        return gestor.agregar(nombre, descripcion, tags=tags)
    
    elif subcmd == 'status':
        return gestor.status(args[1] if len(args) > 1 else None)
    
    elif subcmd == 'proximo' or subcmd == 'next':
        return gestor.proximo(args[1] if len(args) > 1 else None)
    
    elif subcmd == 'nota':
        # /proyectos nota Nombre - La nota
        if len(args) < 3:
            return "⚠️ Uso: /proyectos nota Nombre - La nota aquí"
        
        nombre = args[1]
        nota = ' '.join(args[2:]).replace('- ', '').strip()
        return gestor.agregar_nota(nombre, nota)
    
    elif subcmd == 'actualizar' or subcmd == 'update':
        if len(args) < 3:
            return "⚠️ Uso: /proyectos actualizar Nombre - estado=pausado"
        
        nombre = args[1]
        # Buscar = en los args restantes
        valores = {}
        for arg in args[2:]:
            if '=' in arg:
                key, value = arg.split('=', 1)
                valores[key] = value
        
        if valores:
            return gestor.actualizar(nombre, **valores)
        return "⚠️ Uso: /proyectos actualizar Nombre - clave=valor"
    
    else:
        return """📋 *Comandos /proyectos:*

• /proyectos - Lista todos
• /proyectos lista [filtro] - Lista proyectos
• /proyectos add Nombre - descripcióntag2
• /proyectos status [Nombre] - Status de proyecto
• - tag1, /proyectos prox [Nombre] - Próximo paso
• /proyectos nota Nombre - La nota
• /proyectos actualizar Nombre - estado=pausado"""
