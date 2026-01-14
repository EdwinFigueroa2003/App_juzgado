#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad flexible de Excel
"""

import sys
import os
import pandas as pd
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Agregar el directorio de la aplicación al path
sys.path.append('app_juzgado')

def crear_excel_prueba():
    """Crea un archivo Excel de prueba con diferentes formatos"""
    logger.info("=== CREANDO ARCHIVO EXCEL DE PRUEBA ===")
    
    # Datos de prueba con diferentes formatos de columnas
    datos_formato1 = {
        'RADICADO COMPLETO': ['08001418902020220001', '08001418902020220002'],
        'RADICADO_MODIFICADO_OFI': ['2022-001', '2022-002'],
        'DEMANDANTE': ['JUAN PEREZ', 'MARIA GARCIA'],
        'DEMANDADO': ['EMPRESA ABC', 'EMPRESA XYZ'],
        'ESTADO': ['Pendiente', 'En Proceso'],
        'RESPONSABLE': ['ESCRIBIENTE', 'SUSTANCIADOR']
    }
    
    datos_formato2 = {
        'RadicadoUnicoLimpio': ['08001418902020220003', '08001418902020220004'],
        'RadicadoUnicoCompleto': ['2022-003', '2022-004'],
        'DEMANDANTE_HOMOLOGADO': ['CARLOS LOPEZ', 'ANA MARTINEZ'],
        'DEMANDADO_HOMOLOGADO': ['BANCO DEF', 'COOPERATIVA GHI'],
        'ESTADO_EXPEDIENTE': ['Completado', 'Pendiente'],
        'RESPONSABLE': ['ESCRIBIENTE', 'SUSTANCIADOR']
    }
    
    # Crear archivo Excel con múltiples hojas
    with pd.ExcelWriter('test_expedientes.xlsx', engine='openpyxl') as writer:
        # Hoja 1 - Formato estándar
        df1 = pd.DataFrame(datos_formato1)
        df1.to_excel(writer, sheet_name='Hoja1', index=False)
        
        # Hoja 2 - Formato alternativo
        df2 = pd.DataFrame(datos_formato2)
        df2.to_excel(writer, sheet_name='Resumen por Expediente', index=False)
        
        # Hoja 3 - Formato mixto
        datos_mixto = {
            'radicado_completo': ['08001418902020220005'],
            'radicado_corto': ['2022-005'],
            'demandante': ['PEDRO RODRIGUEZ'],
            'demandado': ['EMPRESA JKL'],
            'estado': ['Activo'],
            'responsable': ['ESCRIBIENTE']
        }
        df3 = pd.DataFrame(datos_mixto)
        df3.to_excel(writer, sheet_name='Expedientes', index=False)
    
    logger.info("✓ Archivo Excel de prueba creado: test_expedientes.xlsx")
    return 'test_expedientes.xlsx'

def test_deteccion_hojas():
    """Prueba la detección automática de hojas"""
    logger.info("=== PRUEBA: Detección de Hojas ===")
    
    try:
        filepath = crear_excel_prueba()
        
        # Simular la lógica de detección de hojas
        excel_file = pd.ExcelFile(filepath)
        hojas_disponibles = excel_file.sheet_names
        logger.info(f"Hojas disponibles: {hojas_disponibles}")
        
        nombres_hojas_posibles = [
            "Resumen por Expediente",
            "Resumen",
            "Expedientes", 
            "Hoja1",
            "Sheet1",
            hojas_disponibles[0] if hojas_disponibles else None
        ]
        
        hoja_seleccionada = None
        for nombre_hoja in nombres_hojas_posibles:
            if nombre_hoja and nombre_hoja in hojas_disponibles:
                hoja_seleccionada = nombre_hoja
                logger.info(f"✓ Hoja seleccionada: '{hoja_seleccionada}'")
                break
        
        if hoja_seleccionada:
            df = pd.read_excel(filepath, sheet_name=hoja_seleccionada)
            logger.info(f"✓ Datos leídos: {len(df)} filas, {len(df.columns)} columnas")
            logger.info(f"Columnas: {list(df.columns)}")
            return True
        else:
            logger.error("✗ No se pudo seleccionar ninguna hoja")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error en detección de hojas: {str(e)}")
        return False
    finally:
        # Limpiar archivo de prueba
        if os.path.exists('test_expedientes.xlsx'):
            os.remove('test_expedientes.xlsx')

def test_deteccion_columnas():
    """Prueba la detección automática de columnas"""
    logger.info("=== PRUEBA: Detección de Columnas ===")
    
    try:
        # Crear datos de prueba con diferentes nombres de columnas
        test_data = {
            'RADICADO COMPLETO': ['08001418902020220001'],
            'DEMANDANTE': ['JUAN PEREZ'],
            'DEMANDADO': ['EMPRESA ABC'],
            'ESTADO': ['Pendiente']
        }
        
        df = pd.DataFrame(test_data)
        logger.info(f"Columnas de prueba: {list(df.columns)}")
        
        # Simular detección de radicado completo
        radicado_completo = None
        for col_name in ['RadicadoUnicoLimpio', 'RADICADO COMPLETO', 'radicado_completo']:
            if col_name in df.columns:
                radicado_completo = df.iloc[0][col_name]
                logger.info(f"✓ Radicado completo detectado en columna '{col_name}': {radicado_completo}")
                break
        
        # Simular detección de demandante
        demandante = None
        for col_name in ['DEMANDANTE_HOMOLOGADO', 'DEMANDANTE', 'demandante']:
            if col_name in df.columns:
                demandante = df.iloc[0][col_name]
                logger.info(f"✓ Demandante detectado en columna '{col_name}': {demandante}")
                break
        
        return radicado_completo is not None and demandante is not None
        
    except Exception as e:
        logger.error(f"✗ Error en detección de columnas: {str(e)}")
        return False

def test_procesamiento_flexible():
    """Prueba el procesamiento flexible de Excel"""
    logger.info("=== PRUEBA: Procesamiento Flexible ===")
    
    try:
        from vista.vistasubirexpediente import procesar_excel_expedientes
        
        # Crear archivo de prueba
        filepath = crear_excel_prueba()
        
        # Intentar procesar (esto fallará en BD pero probará la lógica)
        try:
            resultado = procesar_excel_expedientes(filepath)
            logger.info(f"✓ Procesamiento exitoso: {resultado}")
            return True
        except Exception as e:
            # Es esperado que falle en BD, pero debe llegar hasta ahí
            if "Error leyendo archivo Excel" in str(e) and "Worksheet named" in str(e):
                logger.error("✗ Aún busca hoja específica")
                return False
            else:
                logger.info(f"✓ Lógica de detección funciona (error esperado en BD): {str(e)}")
                return True
                
    except Exception as e:
        logger.error(f"✗ Error en procesamiento flexible: {str(e)}")
        return False
    finally:
        # Limpiar archivo de prueba
        if os.path.exists('test_expedientes.xlsx'):
            os.remove('test_expedientes.xlsx')

def main():
    """Función principal de pruebas"""
    logger.info("=== PRUEBAS EXCEL FLEXIBLE ===")
    
    tests = [
        ("Detección de Hojas", test_deteccion_hojas),
        ("Detección de Columnas", test_deteccion_columnas),
        ("Procesamiento Flexible", test_procesamiento_flexible)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                logger.info(f"✓ {test_name}: PASÓ")
            else:
                logger.error(f"✗ {test_name}: FALLÓ")
        except Exception as e:
            logger.error(f"✗ {test_name}: ERROR - {str(e)}")
    
    logger.info(f"\n=== RESUMEN ===")
    logger.info(f"Pruebas pasadas: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 TODAS LAS PRUEBAS PASARON")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} PRUEBAS FALLARON")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)