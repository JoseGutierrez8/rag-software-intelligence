"""
Actualiza los ejemplos del sidebar al tema de inventario.
Ejecutar desde rag_software_intelligence:
  python fix_sidebar_inventario.py
"""
with open("ui/app.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '''    ejemplos = [
        "En que archivos se usa el campo id_cliente?",
        "Explica la arquitectura del sistema",
        "Que archivos cambian si modifico el campo estado?",
        "Como se relaciona el modelo Cliente con la API?",
        "Que tablas tiene la base de datos y sus relaciones?",
    ]'''

new = '''    ejemplos = [
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

if old in content:
    content = content.replace(old, new)
    with open("ui/app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Sidebar actualizado con ejemplos del sistema de inventario.")
    print("Reinicia Streamlit: Ctrl+C y luego streamlit run ui/app.py")
else:
    print("No se encontro el bloque. El sidebar podria ya estar actualizado.")
