from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
from logica_cotizador import SoatQuotator

app = FastAPI()

# Inicializamos el motor de cotización al arrancar el servidor en Render
motor = SoatQuotator()
try:
    motor.cargar_datos('rimac.xlsx', 'positiva.xlsx', 'pacifico.xlsx', 'protecta.xlsx', 'mapfre.xlsx')
    motor.obtener_catalogo_vehiculos()
    motor.obtener_clases_vehiculo()
    print("✅ Motor de cotización cargado correctamente en la API.")
except Exception as e:
    print(f"❌ Error al inicializar el motor en la API: {e}")

# Definimos el modelo de datos que enviará Zoho SalesIQ
class DatosSOAT(BaseModel):
    placa: str
    marca: str
    modelo: str
    clase: str
    uso: str
    asientos: str
    departamento: str

@app.post("/cotizar")
async def cotizar_soat(datos: DatosSOAT):
    try:
        # Ejecutamos tu motor real usando los datos que mandó el bot de WhatsApp
        df = motor.cotizar(
            departamento="LIMA", 
            uso=datos.uso, 
            clase=datos.clase, 
            asientos=int(datos.asientos), 
            marca=datos.marca, 
            modelo=datos.modelo
        )
        
        tarifas_calculadas = []
        if df is not None and not df.empty:
            df_valid = df[df['Precio'] != "Consultar"].copy()
            if not df_valid.empty:
                df_valid['Precio_Num'] = pd.to_numeric(df_valid['Precio'], errors='coerce')
                for _, row in df_valid.iterrows():
                    if pd.notnull(row['Precio_Num']):
                        tarifas_calculadas.append({
                            "aseguradora": row['Aseguradora'],
                            "precio": float(row['Precio_Num'])
                        })

        # 1. Ordenamos de más barato a más caro
        tarifas_ordenadas = sorted(tarifas_calculadas, key=lambda x: x['precio'])

        # 2. Filtro anti-bloqueo Meta (Máximo Top 3 opciones)
        top_3 = tarifas_ordenadas[:3]

        # 3. Preparamos las opciones dinámicas para Zoho
        opciones_disponibles = []
        for tarifa in top_3:
            precio_formateado = f"S/ {tarifa['precio']:.2f}"
            opciones_disponibles.append({
                "id": tarifa['aseguradora'], 
                "text": f"{tarifa['aseguradora']} - {precio_formateado}"
            })

        # 4. Escenario a prueba de fallas (0 opciones)
        if len(opciones_disponibles) == 0:
            return {
                "mensaje": f"⚠️ Para tu {datos.marca} {datos.modelo} ({datos.placa}) necesitamos realizar una cotización manual con nuestros especialistas.",
                "link_legal": "",
                "botones_dinamicos": [{"id": "asesor", "text": "🙋‍♂️ Hablar con un asesor"}]
            }

        # 5. Escenario exitoso con las mejores opciones
        return {
            "mensaje": f"✅ ¡Listo! Tenemos las mejores opciones para tu {datos.marca} {datos.modelo} con placa {datos.placa}:",
            "link_legal": "https://acrobat.adobe.com/id/urn:aaid:sc:US:5b9c83f9-6972-4a86-aeb4-795f74c62d5a",
            "botones_dinamicos": opciones_disponibles
        }

    except Exception as e:
        return {
            "mensaje": f"⚠️ Ocurrió un error interno al procesar la cotización: {str(e)}",
            "link_legal": "",
            "botones_dinamicos": [{"id": "asesor", "text": "🙋‍♂️ Hablar con un asesor"}]
        }
