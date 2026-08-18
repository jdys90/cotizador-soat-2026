from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
from logica_cotizador import SoatQuotator

app = FastAPI()

# Inicializamos el motor
motor = SoatQuotator()
try:
    motor.cargar_datos('rimac.xlsx', 'positiva.xlsx', 'pacifico.xlsx', 'protecta.xlsx', 'mapfre.xlsx')
    motor.obtener_catalogo_vehiculos()
    motor.obtener_clases_vehiculo()
    print("✅ Motor de cotización cargado correctamente en la API.")
except Exception as e:
    print(f"❌ Error al inicializar el motor en la API: {e}")

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
        departamento_limpio = datos.departamento.upper().strip()
        uso_limpio = datos.uso.upper().strip()

        df = motor.cotizar(
            departamento=departamento_limpio,
            uso=uso_limpio,
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

        tarifas_ordenadas = sorted(tarifas_calculadas, key=lambda x: x['precio'])
        top_3 = tarifas_ordenadas[:3]

        opciones_disponibles = []
        for tarifa in top_3:
            precio_formateado = f"S/ {tarifa['precio']:.2f}"
            opciones_disponibles.append(f"{tarifa['aseguradora']} - {precio_formateado}")

        if len(opciones_disponibles) == 0:
            return {
                "mensaje": f"⚠️ Para tu {datos.marca} {datos.modelo} ({datos.placa}) necesitamos realizar una cotización manual.",
                "link": "",
                "botones": ["🙋‍♂️ Hablar con un asesor"]
            }

        return {
            "mensaje": f"✅ ¡Listo! Tenemos las mejores opciones para tu {datos.marca} {datos.modelo} con placa {datos.placa}:",
            "link": "https://acrobat.adobe.com/id/urn:aaid:sc:US:5b9c83f9-6972-4a86-aeb4-795f74c62d5a",
            "botones": opciones_disponibles
        }

    except Exception as e:
        return {
            "mensaje": f"⚠️ Error al procesar: {str(e)}",
            "link": "",
            "botones": ["🙋‍♂️ Hablar con un asesor"]
        }
