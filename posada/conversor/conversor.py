def conversor_temerant(po: int = 0, pp: int = 0, pc: int = 0):
    """
    Convierte monedas de D&D a la economía de El Asesino de Reyes.
    Utiliza una unidad base entera para evitar errores de precisión de punto flotante.
    """

    monedas_temerant = {
        "Marco": 3520000,
        "Real": 880000,
        "Talento": 352000,
        "Iota / Penique de Plata": 35200,  # Valen lo mismo
        "Sueldo": 11000,
        "Drabín / Penique de Cobre": 3520,  # Valen lo mismo
        "Penique de Hierro": 704,
        "Medio Penique": 352,
        "Ardite": 320
    }

    # 1 PC = 1 Drabín = 3520 unidades base
    total_unidades = (po * 352000) + (pp * 35200) + (pc * 3520)

    print(f"--- Conversión para: {po} PO, {pp} PP, {pc} PC ---")

    # --- Bolsa Óptima ---
    print("\n[BOLSA DE MONEDAS ÓPTIMA]")
    unidades_restantes = total_unidades
    bolsa = {}

    for nombre, valor in monedas_temerant.items():
        if unidades_restantes >= valor:
            cantidad = unidades_restantes // valor
            bolsa[nombre] = cantidad
            unidades_restantes %= valor

    for moneda, cantidad in bolsa.items():
        print(f"- {cantidad}x {moneda}")

    if unidades_restantes > 0:
        print(
            f"(Sobrante de redondeo inaplicable: {unidades_restantes} unidades base)")

    # --- Equivalencia Total Directa ---
    print("\n[EN UNA SOLA DENOMINACIÓN]")
    for nombre, valor in monedas_temerant.items():
        # Usamos round para mostrar equivalencias aproximadas en denominaciones mayores
        cantidad_total = total_unidades / valor
        if cantidad_total >= 1 or nombre == "Ardite":
            # Formatear para no mostrar decimales innecesarios si es exacto
            formato_cantidad = f"{cantidad_total:.2f}".rstrip('0').rstrip('.')
            print(f"Equivale a: {formato_cantidad}x {nombre}")


if __name__ == "__main__":
    # Cambiar los valores de po, pp y pc para probar diferentes conversiones
    conversor_temerant(po=9, pp=0, pc=0)
