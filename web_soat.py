import streamlit as st
import pandas as pd
import datetime
import re
import os
import smtplib
import gspread
import pytz # LIBRERÍA PARA ZONA HORARIA


from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from logica_cotizador import SoatQuotator

# 👇 AQUÍ ESTÁ LA MAGIA: Importamos ambas funciones desde generador_pdf
from generador_pdf import crear_pdf, exportar_pdf_a_png 

# ... (El resto de tu código, como def mostrar_panel_administrador():) ...
def aplicar_estilos_css():
    st.markdown("""
    <style>
        :root {
            /* Modo Día */
            --bg-color: #F8F9FA;
            --table-bg: #FFFFFF;
            --text-main: #212529;
            --header-bg: #f0f2f6;
            --accent-color: #0066CC;
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --bg-color: #121212;
                --table-bg: #1E1E1E;
                --text-main: #E0E0E0;
                --header-bg: #2D2D2D;
                --accent-color: #4D9FE5;
            }
        }

      /* Aplicación global de estilos */
        .stApp {
            background-color: var(--bg-color);
            color: var(--text-main);
        }
        
        /* Estilos específicos para tus tablas de cotización */
        table {
            background-color: var(--table-bg) !important;
            color: var(--text-main) !important;
        }
        
        /* Botón de acción principal */
        .stButton>button {
            background-color: var(--accent-color) !important;
            color: white !important;
            border-radius: 5px;
                /* Opcional: efecto hover (cuando pasas el mouse) */
    div[data-testid="stButton>button"] button:hover {
        opacity: 0.9;
        }
    </style>
    """, unsafe_allow_html=True)

# Llama a la función al inicio de tu script
aplicar_estilos_css()

def mostrar_panel_administrador():
    """Muestra el panel de edición de tarifas con soporte para múltiples hojas."""
    st.header("⚙️ Panel de Administración de Tarifas")
    st.info("💡 Haz doble clic en cualquier celda para modificarla. Usa la última fila vacía para agregar nuevas opciones.")

    DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
    aseguradoras = ["rimac", "pacifico", "mapfre", "positiva", "protecta"]
    
    # 1. Selector de aseguradora
    aseguradora = st.selectbox("Selecciona la Aseguradora a editar:", aseguradoras)
    
    nombre_archivo = f"{aseguradora}.xlsx"
    ruta_archivo = os.path.join(DIRECTORIO_ACTUAL, nombre_archivo)

    if os.path.exists(ruta_archivo):
        try:
            # 2. Leemos el archivo Excel para descubrir qué hojas tiene adentro
            xls = pd.ExcelFile(ruta_archivo)
            hojas_disponibles = xls.sheet_names
            
            # 3. Selector de hoja
            hoja_seleccionada = st.selectbox("Selecciona la hoja que deseas editar (ej. Tarifario, Modelos):", hojas_disponibles)
            
            # 4. Cargamos solo la hoja que el usuario eligió
            df_hoja = pd.read_excel(ruta_archivo, sheet_name=hoja_seleccionada)

            # 👇 --- NUEVO CÓDIGO: LIMPIEZA DE COLUMNAS MIXTAS --- 👇
            # Forzamos a que las columnas problemáticas sean tratadas como texto puro
            for col in df_hoja.columns:
                if df_hoja[col].dtype == 'object':
                    df_hoja[col] = df_hoja[col].fillna("").astype(str)
            # --------------------------------------------------------
            
            # 5. Mostramos el editor de datos
            df_editado = st.data_editor(
                df_hoja, 
                num_rows="dynamic", 
                use_container_width=True,
                # Usamos una clave única para que Streamlit no confunda las tablas al cambiar de hoja
                key=f"editor_{aseguradora}_{hoja_seleccionada}" 
            )
            
            # 6. Guardado Blindado (Evita borrar las otras hojas)
            if st.button("💾 Guardar Cambios Definitivos", type="primary"):
                try:
                    # Usamos ExcelWriter en modo 'a' (append/añadir) y 'replace' (reemplazar solo esta hoja)
                    with pd.ExcelWriter(ruta_archivo, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                        df_editado.to_excel(writer, sheet_name=hoja_seleccionada, index=False)
                        
                    st.success(f"✅ ¡La hoja '{hoja_seleccionada}' de {aseguradora.capitalize()} se actualizó de forma segura!")
                except Exception as e:
                    st.error(f"Error crítico al intentar guardar el archivo: {e}")
                    
        except Exception as e:
            st.error(f"Error al leer el archivo Excel. Asegúrate de que no esté corrupto: {e}")
    else:
        st.error(f"No se encontró el archivo en: {ruta_archivo}")


# --- 📧 CONFIGURACIÓN DE CORREO ZOHO ---
SMTP_SERVER = "smtppro.zoho.com"
SMTP_PORT = 587
EMAIL_SENDER = "administracion@yqcorredores.com"
EMAIL_RECEIVER = "administracion@yqcorredores.com" 

# 👇 CAMBIO IMPORTANTE: YA NO ESCRIBIMOS LA CLAVE AQUÍ
# Le decimos al sistema que la busque en los "Secretos"
try:
    EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]
except FileNotFoundError:
    # Esto es por si corres la app en tu PC y no has configurado el archivo de secretos
    EMAIL_PASSWORD = "" 
    st.warning("⚠️ Falta configurar el secreto del correo.")

# --- ☁️ CONEXIÓN A GOOGLE SHEETS ---
def conectar_google_sheets():
    try:
        if "gcp_service_account" in st.secrets:
            gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
            sh = gc.open("historial_soat") 
            worksheet = sh.sheet1
            return worksheet
        else:
            return None
    except Exception as e:
        print(f"Error conectando a Google Sheets: {e}")
        return None

def guardar_historial_google(fecha, hora, cot_id, rol, cliente, dni, celular, email, placa, marca, modelo, uso, precio_ref, cia_min, precio_min, es_campana):
    """Guarda en la nube con DATOS DE COMPETENCIA."""
    worksheet = conectar_google_sheets()
    if worksheet:
        try:
            worksheet.append_row([
                fecha, hora, cot_id, rol, cliente, dni, celular, email, 
                placa, marca, modelo, uso, precio_ref, cia_min, precio_min, es_campana
            ])
            print("✅ Guardado en Google Sheets")
        except Exception as e:
            print(f"❌ Error escribiendo en Google Sheets: {e}")

def descargar_historial_google():
    worksheet = conectar_google_sheets()
    if worksheet:
        try:
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except Exception as e:
            st.error(f"Error leyendo Google Sheets: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def guardar_historial_local(fecha, hora, cot_id, rol, cliente, dni, celular, email, placa, marca, modelo, uso, precio_ref, cia_min, precio_min, es_campana):
    """Guarda en CSV local con DATOS DE COMPETENCIA."""
    archivo_csv = "historial_cotizaciones.csv"
    data = {
        "Fecha": [fecha], "Hora": [hora], "ID": [cot_id], "Rol": [rol],
        "Cliente": [cliente], "DNI_RUC": [dni], "Celular": [celular], "Email": [email],
        "Placa": [placa], "Marca": [marca], "Modelo": [modelo], "Uso": [uso], 
        "Precio_Ref": [precio_ref], "Cia_Min": [cia_min], "Precio_Min": [precio_min], "Es_Campaña": [es_campana]
    }
    df_new = pd.DataFrame(data)
    
    if not os.path.exists(archivo_csv):
        df_new.to_csv(archivo_csv, index=False, encoding='utf-8-sig')
    else:
        df_new.to_csv(archivo_csv, mode='a', header=False, index=False, encoding='utf-8-sig')

def enviar_notificacion(cot_id, fecha_hora, rol, cliente, celular, placa, marca, modelo, precio_min, cia_min):
    """Envía correo avisando de nueva cotización."""
    try:
        # Si la clave está vacía (no se configuraron secretos), no hace nada.
        if not EMAIL_PASSWORD or len(EMAIL_PASSWORD) < 5: 
            print("⚠️ No hay contraseña configurada en Secrets. Correo omitido.")
            return 
        
        subject = f"🔔 Nueva Cotización SOAT: {cliente} ({placa})"
        body = f"""
        <h3>Nueva Cotización Generada</h3>
        <ul>
            <li><b>ID:</b> {cot_id}</li>
            <li><b>Fecha:</b> {fecha_hora}</li>
            <li><b>Rol:</b> {rol}</li>
            <li><b>Cliente:</b> {cliente}</li>
            <li><b>DNI:</b> {dni}</li> <li><b>Celular:</b> {celular}</li>
            <li><b>Vehículo:</b> {marca} {modelo} ({placa})</li>
            <li><b>Mejor Oferta:</b> S/ {precio_min} ({cia_min})</li>
        </ul>
        <p>Datos guardados en historial.</p>
        """
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"❌ Error enviando correo: {e}")

st.set_page_config(page_title="Cotizador SOAT Digital", layout="centered", page_icon="🚗")

@st.cache_resource
def iniciar_motor():
    motor = SoatQuotator()
    motor.cargar_datos('rimac.xlsx', 'positiva.xlsx', 'pacifico.xlsx', 'protecta.xlsx', 'mapfre.xlsx')
    motor.obtener_catalogo_vehiculos()
    motor.obtener_clases_vehiculo()
    return motor

try:
    app = iniciar_motor()
    catalogo = app.obtener_catalogo_vehiculos()
    lista_marcas = list(catalogo.keys())
    carga_exitosa = True
except Exception as e:
    st.error(f"Error carga: {e}")
    carga_exitosa = False
    lista_marcas = []

with st.sidebar:
    if pd.io.common.file_exists("logo.png"): st.image("logo.png")
    st.info("🔹 BIENVENIDO")

st.title("COTIZACION SOAT DIGITAL")

if carga_exitosa:
    # --- 1. DATOS DEL CLIENTE ---
    st.subheader("1. Datos del Cliente")
    c1_1, c1_2 = st.columns(2)
    with c1_1: nombre = st.text_input("Nombre Completo")
    with c1_2: dni = st.text_input("DNI / RUC", max_chars=11, placeholder="Solo números")
    
    c2_1, c2_2 = st.columns(2)
    with c2_1: placa = st.text_input("Placa", max_chars=6, placeholder="ABC1234").upper()
    with c2_2: fecha_venc = st.date_input("Vencimiento SOAT", datetime.date.today(), format="dd/dd/yyyy")
    
    c3_1, c3_2 = st.columns(2)
    with c3_1: celular = st.text_input("Celular / Whatsapp", max_chars=9, placeholder="Ej: 999123456")
    with c3_2: email = st.text_input("Correo Electrónico", placeholder="cliente@correo.com")
    
    st.markdown("---")
    
    # --- 2. DATOS DEL VEHICULO ---
    st.subheader("2. Datos del Vehículo")
    c1, c2 = st.columns(2)
    with c1:
        lista_deptos = sorted([
            "LIMA", "AREQUIPA", "CUSCO", "LA LIBERTAD", "LAMBAYEQUE", "PIURA", "JUNIN", 
            "ANCASH", "ICA", "SAN MARTIN", "LORETO", "UCAYALI", "CAJAMARCA", "HUANUCO", 
            "TACNA", "PUNO", "AYACUCHO", "MOQUEGUA", "AMAZONAS", "APURIMAC", 
            "HUANCAVELICA", "MADRE DE DIOS", "PASCO", "TUMBES"
        ])
        try: index_def = lista_deptos.index("LIMA")
        except: index_def = 0
        depto = st.selectbox("📍 Departamento", lista_deptos, index=index_def)
        
        uso = st.selectbox("📋 Uso", ["PARTICULAR", "TAXI", "CARGA", "TRANSPORTE PERSONAL", "URBANO", "INTERPROVINCIAL", "COMERCIAL","AMBULANCIA","SERVICIO ESCOLAR"])
        
        # --- MEJORA UX: Nombres amigables para el cliente ---
        mapa_clases = {
            "AUTOMÓVIL": "AUTOMOVIL",
            "STATION WAGON": "SW",
            "CAMIONETA RURAL / SUV": "SUV",
            "MULTIPROPÓSITO": "MULTIPROPOSITO",
            "CAMIONETA PANEL": "PANEL",
            "CAMIONETA VAN": "VAN",
            "MICROBUS": "MICROBUS",
            "MINIBUS": "MINIBUS",
            "OMNIBUS": "OMNIBUS",
            "CAMIONETA PICK UP": "PICK UP",      
            "CAMIÓN BARANDA / FURGÓN": "CAMION",
            "CAMIÓN REMOLCADOR": "REMOLCADOR",
            "MAQUINARIA PESADA": "MAQUINARIA PESADA",
            "MOTO LINEAL": "MOTOCICLETA",
            "MOTO ELÉCTRICA": "MOTOCICLETA ELECTRICA",
            "TRIMOTO": "TRIMOTO",
            "CUATRIMOTO": "CUATRIMOTO",
            "MOTO FURGONETA": "FURGONETA"
        }
        clase_display = st.selectbox("🚙 Clase", list(mapa_clases.keys()))
        clase_interna = mapa_clases[clase_display]
        
        asientos = st.number_input("💺 Asientos", 1, 70, 5)
        
    with c2:
        marca = st.selectbox("🚘 Marca", ["OTRA MARCA"] + lista_marcas)
        if marca == "OTRA MARCA":
            marca_txt = st.text_input("Ingresa Marca:").upper()
            modelo_opts = []
        else:
            marca_txt = marca
            modelo_opts = catalogo.get(marca, [])
        
        usar_manual = st.checkbox("✍️ Escribir modelo manualmente")
        if usar_manual:
            modelo_txt = st.text_input("Escribe el Modelo:", "").upper()
        else:
            mod = st.selectbox("🚙 Modelo", modelo_opts + ["OTRO MODELO"])
            modelo_txt = st.text_input("Especificar Otro:", "").upper() if mod == "OTRO MODELO" else mod

    st.markdown("---")

    # --- 3. CODIGO ADMIN ---
    col_code, col_btn = st.columns([1, 1])
    with col_code:
        codigo_admin = st.text_input("Código de Descuento (Opcional)", type="password", placeholder="Si tienes uno, ingrésalo aquí")
    
    es_admin = (codigo_admin == "ADMIN2026")

    if es_admin:
        # Llama a la función AQUÍ para que aparezca la tabla
    
        if st.button("📥 DESCARGAR HISTORIAL (Google Sheets)"):
            df_historial = descargar_historial_google()
            if not df_historial.empty:
                csv = df_historial.to_csv(index=False).encode('utf-8-sig')
                st.download_button("💾 Clic para guardar CSV", csv, f"Historial_{datetime.datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
            else:
                st.warning("No se pudo conectar a Google Sheets o la hoja está vacía.")

    if 'res' not in st.session_state: st.session_state.res = None
    if 'id' not in st.session_state: st.session_state.id = None

    if col_btn.button("🔍 GENERAR COTIZACIÓN", use_container_width=True):
        errores = []
        if not nombre: errores.append("Falta el Nombre.")
        if not dni or not dni.isdigit(): errores.append("Ingrese un DNI/RUC válido.")
        if not marca_txt or not modelo_txt: errores.append("Faltan datos del vehículo.")
        if not placa or len(placa) != 6 or not placa.isalnum(): errores.append("La PLACA debe tener exactamente 6 caracteres alfanuméricos.")
        
        if not es_admin:
            if not celular or not celular.isdigit() or len(celular) < 9: errores.append("Ingrese un celular válido.")
            if not email or "@" not in email: errores.append("Ingrese un correo válido.")

        if errores:
            for e in errores: st.error(e)
        else:
            with st.spinner("Cotizando..."):
                # OBTENER HORA EXACTA PERÚ
                peru_tz = pytz.timezone('America/Lima')
                now = datetime.datetime.now(peru_tz) # <-- AQUÍ ESTÁ EL CAMBIO CLAVE
                df = app.cotizar(depto, uso, clase_interna, asientos, marca_txt, modelo_txt)
                st.session_state.res = df
                st.session_state.id = f"2000-{datetime.datetime.now().strftime('%m%d-%H%M')}"
                
                rol_actual = "ADMIN" if es_admin else "CLIENTE"
                
                # Inteligencia de Precios
                min_cia = "-"
                min_precio = 0
                min_campana = "NO"
                precio_ref = 0
                
                if not df.empty:
                    df_valid = df[df['Precio'] != "Consultar"].copy()
                    if not df_valid.empty:
                        df_valid['Precio_Num'] = pd.to_numeric(df_valid['Precio'], errors='coerce')
                        df_valid = df_valid.sort_values(by='Precio_Num', ascending=True)
                        mejor = df_valid.iloc[0]
                        min_cia = mejor['Aseguradora']
                        min_precio = float(mejor['Precio_Num'])
                        min_campana = "SI" if mejor['Tiene_Campaña'] else "NO"
                        precio_ref = min_precio
                
              # FORMATOS DE FECHA LOCALIZADOS
                f_log = now.strftime('%Y-%m-%d')
                h_log = now.strftime('%H:%M:%S')
                f_email = now.strftime('%d/%m/%Y %I:%M %p')
                
                guardar_historial_local(f_log, h_log, st.session_state.id, rol_actual, nombre, dni, celular, email, placa, marca_txt, modelo_txt, uso, precio_ref, min_cia, min_precio, min_campana)
                guardar_historial_google(f_log, h_log, st.session_state.id, rol_actual, nombre, dni, celular, email, placa, marca_txt, modelo_txt, uso, precio_ref, min_cia, min_precio, min_campana)
                
                if not es_admin:
                    enviar_notificacion(st.session_state.id, f_email, rol_actual, nombre, celular, placa, marca_txt, modelo_txt, min_precio, min_cia)
        df_visible = pd.DataFrame() 

if st.session_state.res is not None:
# 1. TRUCO DE MEMORIA: Creamos una copia editable que no se sobreescriba al recargar
    if 'id_cotizacion_actual' not in st.session_state or st.session_state.id_cotizacion_actual != st.session_state.id:
        df_base = st.session_state.res.copy()
        st.session_state.df_editable = df_base[df_base['Precio'] != "Consultar"]
        st.session_state.id_cotizacion_actual = st.session_state.id

    # Usamos nuestra copia editable
    df_visible = st.session_state.df_editable

    if not df_visible.empty:
        st.success(f"Cotización N° {st.session_state.id}")
        if es_admin: 
            st.info("🔓 MODO CORREDOR ACTIVADO - Ajusta los precios u observaciones antes de generar el PDF:")
        # 2. INYECTAMOS EL EDITOR DE DATOS SOLO PARA EL ADMIN
            df_visible = st.data_editor(
                df_visible,
                # Bloqueamos lo que no se debe tocar para no romper la lógica
                disabled=["Aseguradora", "Grupo", "Comision_pct", "Tiene_Campaña", "Precio_Lista"],
                use_container_width=True,
                hide_index=True,
                key=f"editor_rapido_{st.session_state.id}"
            )
            # 3. Guardamos los cambios inmediatamente en la memoria
            st.session_state.df_editable = df_visible
            st.markdown("---") # Separador visual
            
        df_visible['Precio_Num'] = pd.to_numeric(df_visible['Precio'], errors='coerce').fillna(0)
        df_visible['Comisión S/.'] = (df_visible['Precio_Num'] / 1.2154) * df_visible['Comision_pct']
        df_visible['% Com'] = df_visible['Comision_pct'].apply(lambda x: f"{x*100:.0f}%")
        
        html_rows = ""
        for _, row in df_visible.iterrows():
            # Nota: Dejamos algunos colores específicos (como rojo para descuentos) 
            # porque son lógica de negocio, no solo diseño.
            precio_cell = ""
            tiene_promo = row['Tiene_Campaña'] and row['Precio_Lista'] != "Consultar"
            if tiene_promo:
                try:
                    p_old = float(row['Precio_Lista']); p_new = float(row['Precio'])
                    if p_new < p_old: 
                        precio_cell = f"<div><span style='text-decoration:line-through; color:#999; font-size:13px;'>S/ {p_old:.2f}</span><br><span style='color:#d32f2f; font-weight:bold; font-size:16px;'>S/ {p_new:.2f}</span></div>"
                    else: precio_cell = f"<span style='color:inherit; font-weight:bold; font-size:16px;'>S/ {p_new:.2f}</span>"
                except: precio_cell = f"<span style='color:inherit; font-weight:bold; font-size:16px;'>{row['Precio']}</span>"
            else:
                try: val = float(row['Precio']); precio_cell = f"<span style='color:inherit; font-weight:bold; font-size:16px;'>S/ {val:.2f}</span>"
                except: precio_cell = f"<span style='color:inherit; font-weight:bold; font-size:16px;'>{row['Precio']}</span>"

            obs_txt = str(row['Observaciones']).replace('🔥', '').strip()
            if obs_txt == "nan": obs_txt = ""
            
            if es_admin:
                com_txt = f"{row['% Com']} (S/ {row['Comisión S/.']:.2f})"
                grupo_txt = str(row.get('Grupo', '-'))
                html_rows += f"<tr><td><b>{row['Aseguradora']}</b></td><td>{grupo_txt}</td><td>{precio_cell}</td><td>{com_txt}</td><td>{obs_txt}</td></tr>"
            else:
                html_rows += f"<tr><td><b>{row['Aseguradora']}</b></td><td>{precio_cell}</td><td>{obs_txt}</td></tr>"

        if es_admin:
            header = "<th>ASEGURADORA</th><th>GRUPO</th><th>PRECIO</th><th>COMISIÓN</th><th>OBSERVACIONES</th>"
        else:
            header = "<th>ASEGURADORA</th><th>PRECIO FINAL</th><th>OBSERVACIONES</th>"

        # Esta es la clase 'resultado-table' que definimos en el CSS anterior
        st.markdown(f"""
        <div class='table-container'>
            <table class='resultado-table'>
                <thead>
                    <tr>{header}</tr>
                </thead>
                <tbody>
                    {html_rows}
                </tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)
        
        obs_pdf = " / ".join(df_visible[df_visible['Observaciones'] != ""]['Observaciones'].unique()).replace('🔥', '').strip()
        campanas_list = df_visible[df_visible['Tiene_Campaña'] == True]['Aseguradora'].unique().tolist()
        campanas_txt = ", ".join(campanas_list) if campanas_list else ""

        pdf_bytes = crear_pdf(
            cotizacion_nro=st.session_state.id,
            cliente=nombre, dni_ruc=dni, celular=celular, email=email,
            placa=placa, marca=marca_txt, modelo=modelo_txt,
            uso=uso, clase=clase_display, asientos=asientos, region=depto,
            fecha_vencimiento=fecha_venc.strftime('%d/%m/%Y'),
            df_resultados=df_visible,
            observaciones_especiales=obs_pdf,
            campanas_activas_txt=campanas_txt
        )
        
    # ... (aquí arriba está tu código de pdf_bytes = crear_pdf(...))

        def limpiar_txt(t): return re.sub(r'[^\w\s-]', '', str(t)).strip().replace(' ', '_')
        nombre_base = f"COTISOAT_{limpiar_txt(nombre)}_{limpiar_txt(marca_txt)}_{limpiar_txt(modelo_txt)}_{limpiar_txt(uso)}_{datetime.datetime.now().strftime('%d%m%y_%H%M')}"
        st.markdown("""
    <style>
    /* Estilo para el botón de PDF (Dorado) */
    div[data-testid="stDownloadButton"]:nth-of-type(1) button {
    background-color: #bf8d1b !important;
    color: white !important;
    border: 1px solid #bf8d1b !important;
    }

    /* Estilo para el botón de Imagen (Verde) */
    div[data-testid="stDownloadButton"]:nth-of-type(2) button {
    background-color: #089685 !important;
    color: white !important;
    border: 1px solid #089685 !important;
    }

    /* Opcional: efecto hover (cuando pasas el mouse) */
    div[data-testid="stDownloadButton"] button:hover {
    opacity: 0.9;
    }
    </style>
    """, unsafe_allow_html=True)
        # --- NUEVO CÓDIGO DE DESCARGA ---
        st.success("✅ ¡Cotización calculada y documentos generados con éxito!")
        
        # Convertimos los bytes del PDF directamente a bytes de PNG
        png_bytes = exportar_pdf_a_png(pdf_bytes)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📄 Descargar PDF", 
                data=pdf_bytes, 
                file_name=f"{nombre_base}.pdf", 
                mime="application/pdf",  
                use_container_width=True
            )
            
        with col2:
            if png_bytes:
                st.download_button(
                    label="🖼️ Descargar Imagen", 
                    data=png_bytes, 
                    file_name=f"{nombre_base}.png", 
                    mime="image/png", 
                    use_container_width=True
                )
            else:
                st.error("Error al generar PNG")
        
    else:
        st.error("No hay precios disponibles.")          
# --- PANEL DE ADMINISTRACIÓN (FUERA DEL BOTÓN) ---
if es_admin:
    st.markdown("---")
    mostrar_panel_administrador()