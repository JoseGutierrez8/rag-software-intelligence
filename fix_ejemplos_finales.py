"""
Actualiza los ejemplos del sidebar con las preguntas validadas.
Ejecutar desde rag_software_intelligence:
  python fix_ejemplos_finales.py
"""
with open("ui/app.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '''    ejemplos = [
        "Que tablas tiene el sistema y cuales son sus relaciones?",
        "En que archivos se usa el campo id_producto?",
        "Explica las capas de la arquitectura del sistema de inventario",
        "Que hace la funcion registrar_entrada y que archivos involucra?",
        "Si cambio el campo stock_minimo, que archivos se veerian afectados?",
        "Que roles de usuario existen y que permisos tiene cada uno?",
        "Como funciona el ciclo de vida de un pedido de compra?",
        "Que tipos de movimiento de inventario existen?",
        "Que campos tiene la tabla movimientos y para que sirve cada uno?",
        "Como se generan las alertas de stock minimo en el codigo?",
    ]'''

new = '''    ejemplos = [
        "Que tablas define el Diccionario_Inventario.xlsx y cuales son sus claves foraneas",
        "En que archivos de codigo se usa el campo id_producto definido en la tabla productos",
        "Explica las capas de la arquitectura del sistema de inventario",
        "Que hace la funcion registrar_entrada y que archivos involucra?",
        "Si cambio el campo stock_minimo, que archivos se veerian afectados?",
        "Cuales son los roles validos en la clase RolUsuario del archivo usuario.py",
        "Como funciona el metodo cambiar_estado en el modelo pedido.py",
        "Que tipos de movimiento de inventario existen?",
        "Que campos tiene la tabla movimientos segun el Diccionario_Inventario.xlsx",
        "Como funciona la funcion verificar_stock_minimo en alerta_service.py",
    ]'''

if old in content:
    content = content.replace(old, new)
    with open("ui/app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Ejemplos actualizados correctamente.")
else:
    print("No se encontro el bloque. Verificando...")
    # Buscar parcialmente
    if '"Que tablas tiene el sistema' in content:
        print("Encontrado parcialmente - aplicando reemplazo linea por linea")
        replacements = [
            ('"Que tablas tiene el sistema y cuales son sus relaciones?"',
             '"Que tablas define el Diccionario_Inventario.xlsx y cuales son sus claves foraneas"'),
            ('"En que archivos se usa el campo id_producto?"',
             '"En que archivos de codigo se usa el campo id_producto definido en la tabla productos"'),
            ('"Que roles de usuario existen y que permisos tiene cada uno?"',
             '"Cuales son los roles validos en la clase RolUsuario del archivo usuario.py"'),
            ('"Como funciona el ciclo de vida de un pedido de compra?"',
             '"Como funciona el metodo cambiar_estado en el modelo pedido.py"'),
            ('"Que campos tiene la tabla movimientos y para que sirve cada uno?"',
             '"Que campos tiene la tabla movimientos segun el Diccionario_Inventario.xlsx"'),
            ('"Como se generan las alertas de stock minimo en el codigo?"',
             '"Como funciona la funcion verificar_stock_minimo en alerta_service.py"'),
        ]
        for old_q, new_q in replacements:
            if old_q in content:
                content = content.replace(old_q, new_q)
                print("  Reemplazado: " + old_q[:50])
        with open("ui/app.py", "w", encoding="utf-8") as f:
            f.write(content)
        print("Listo.")
    else:
        print("No se pudo encontrar los ejemplos. Revisa manualmente ui/app.py")

print("\nReinicia Streamlit:")
print("  streamlit run ui/app.py --server.fileWatcherType none")
