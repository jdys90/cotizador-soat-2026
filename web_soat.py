import streamlit as st
import pandas as pd
import datetime
import re
import os
import smtplib
import gspread
import pytz
import requests
import io
import fitz  # PyMuPDF
from fpdf import FPDF
from difflib import get_close_matches
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y CSS (CRO)
# ==========================================
st.set_page_config(page_title="Cotizador SOAT Digital", layout="centered", page_icon="🚗")

def aplicar_estilos_css():
    st.markdown("""
    <style>
        /* Ocultar cabeceras y pies de página nativos (Fuerza Bruta a nuevos identificadores) */
        #MainMenu, header, footer, [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stBottom"] {
            display: none !important; 
            visibility: hidden !important; 
        }
        
        /* Destruir cualquier rastro de la marca de agua rastreando su enlace */
        a[href^="https://streamlit.io"] { display: none !important; }
        
        /* Ajustar el margen inferior para que el botón verde no quede volando */
        .block-container { padding-bottom: 6rem !important; }

        :root {
            --bg-color: #F8F9FA;
            --table-bg: #FFFFFF;
            --text-main: #212529;
            --header-bg: #f0f2f6;
            --accent-color: #0066CC;
        }

        /* Botón de acción principal (Generar Cotización) */
        div[data-testid="stButton"] button {
            background-color: #2456A6 !important;
            color: white !important;
            border: 2px solid #2456A6 !important;
            padding: 0.75rem 2rem !important;
            font-size: 18px !important;
            font-weight: bold !important;
            border-radius: 8px !important;
        }
        div[data-testid="stButton"] button:hover {
            background-color: #1a428a !important;
            border-color: #1a428a !important;
            color: white !important;
            opacity: 0.9 !important;
        }

        /* Botón WhatsApp */
        div[data-testid="stLinkButton"] a {
            background-color: #25D366 !important; 
            color: white !important; 
            border: 1px solid #25D366 !important;
            border-radius: 8px !important;
            text-decoration: none !important;
            font-weight: 600 !important;
            display: flex !important;
            justify-content: center !important;
            height: 42px !important;
            align-items: center !important;
        }
        
        /* Botón Descargar PDF */
        div[data-testid="stDownloadButton"] button {
            background-color: #2456A6 !important; 
            color: white !important; 
            border: 1px solid #2456A6 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            height: 42px !important;
            width: 100% !important;
        }
    </style>
    """, unsafe_allow_html=True)

aplicar_estilos_css()

# ==========================================
# 2. MOTOR GENERADOR DE PDF
# ==========================================
AZUL = (0, 102, 204)     
FONDO = (245, 250, 255)  
NEGRO = (0, 0, 0)
GRIS = (120, 120, 120)
VERDE_WA = (37, 211, 102)

def exportar_pdf_a_png(pdf_bytes):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pagina = doc.load_page(0)
        mat = fitz.Matrix(2, 2)
        pix = pagina.get_pixmap(matrix=mat)
        return pix.tobytes("png")
    except Exception as e:
        print(f"Error en conversión a PNG: {e}")
        return None

class PDF(FPDF):
    def header(self):
        if os.path.exists("logo.png"): self.image("logo.png", 10, 10, 35)
        self.set_xy(50, 20)
        self.set_font('Arial', 'B', 18); self.set_text_color(*AZUL)
        self.cell(0, 8, 'COTIZACION SOAT DIGITAL', 0, 1, 'R')
        self.set_xy(50, 28); self.set_font('Arial', '', 9); self.set_text_color(100,100,100)
        self.cell(0, 5, 'Documento oficial de cotizacion', 0, 1, 'R')
        self.set_draw_color(*AZUL); self.set_line_width(0.8); self.line(10, 60, 200, 60); self.set_y(68)

    def section_title(self, title):
        self.set_font('Arial', 'B', 12); self.set_text_color(255, 255, 255)
        self.set_fill_color(*AZUL)
        self.cell(0, 8, f"  {title}", 0, 1, 'L', fill=True)
        self.ln(3)

def crear_pdf(cotizacion_nro, cliente, dni_ruc, celular, email, placa, marca, modelo, uso, clase, asientos, region, fecha_vencimiento, df_resultados, observaciones_especiales="", campanas_activas_txt=""):
    pdf = PDF(orientation='P', unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(False)
    pdf.add_page()

    # RESUMEN
    pdf.section_title("RESUMEN DE SOLICITUD")
    pdf.set_fill_color(*FONDO)
    pdf.rect(pdf.get_x(), pdf.get_y(), 190, 42, 'F') 
    y_ini = pdf.get_y() + 2

    # Columna Izq
    pdf.set_xy(15, y_ini); pdf.set_text_color(*NEGRO)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "Cotización:",0,0); pdf.set_font('Arial', 'B', 11); pdf.cell(60, 6, str(cotizacion_nro),0,1)
    pdf.set_x(15); pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "Cliente:",0,0); pdf.set_font('Arial', '', 10); pdf.cell(60, 6, str(cliente)[:35],0,1)
    pdf.set_x(15); pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "DNI/RUC:",0,0); pdf.set_font('Arial', '', 10); pdf.cell(60, 6, str(dni_ruc),0,1)
    if celular:
        pdf.set_x(15); pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "Celular:",0,0); pdf.set_font('Arial', '', 10); pdf.cell(60, 6, str(celular)[:20],0,1)
    pdf.set_x(15); pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "Placa:",0,0); pdf.set_font('Arial', 'B', 10); pdf.cell(60, 6, str(placa),0,1)

    # Columna Der
    x_der = 120
    pdf.set_xy(x_der, y_ini)
    pdf.set_font('Arial', 'B', 9); pdf.cell(32, 6, "F. Cotización:",0,0); pdf.set_font('Arial', '', 10); pdf.cell(40, 6, datetime.datetime.now().strftime('%d/%m/%Y'),0,1)
    pdf.set_xy(x_der, y_ini+6)
    pdf.set_font('Arial', 'B', 9); pdf.cell(32, 6, "Vence SOAT:",0,0); pdf.set_font('Arial', 'B', 10); pdf.cell(40, 6, str(fecha_vencimiento),0,1)
    pdf.set_xy(x_der, y_ini+12)
    pdf.set_font('Arial', 'B', 9); pdf.cell(32, 6, "Región:",0,0); pdf.set_font('Arial', '', 10); pdf.cell(40, 6, str(region),0,1)
    pdf.set_xy(x_der, y_ini+18)
    pdf.set_font('Arial', 'B', 9); pdf.cell(32, 6, "Uso:",0,0); pdf.set_font('Arial', '', 10); pdf.cell(40, 6, str(uso),0,1)
    pdf.set_xy(x_der, y_ini+24)
    pdf.set_font('Arial', 'B', 9); pdf.cell(32, 6, "Asientos:",0,0); pdf.set_font('Arial', '', 10); pdf.cell(40, 6, str(asientos),0,1)
    pdf.set_xy(x_der, y_ini+30)
    pdf.set_font('Arial', 'B', 9); pdf.cell(32, 6, "Vehículo:",0,0); pdf.set_font('Arial', '', 9); pdf.cell(40, 6, f"{marca} {modelo}"[:25],0,1)

    pdf.set_y(y_ini + 45)

    # OFERTAS
    pdf.section_title("OFERTAS DISPONIBLES")
    
    # --- LECTURA AUTOMÁTICA DEL ARCHIVO DE BENEFICIOS ---
    mapa_beneficios = {}
    try:
        import pandas as pd
        df_ben = pd.read_csv('Beneficios_SOAT.csv', sep=None, engine='python', encoding='utf-8-sig')
        df_ben.columns = df_ben.columns.str.strip().str.upper()
        for _, r in df_ben.iterrows():
            cia_csv = str(r.get('COMPAÑÍA', r.get('COMPANIA', ''))).strip().upper()
            # Mapeo inteligente para evitar errores tipográficos
            if "PAC" in cia_csv: c_key = "Pacífico"
            elif "RIM" in cia_csv or "RÍM" in cia_csv: c_key = "Rimac"
            elif "POS" in cia_csv: c_key = "La Positiva"
            elif "MAP" in cia_csv: c_key = "Mapfre"
            elif "PRO" in cia_csv: c_key = "Protecta"
            else: c_key = str(r['COMPAÑÍA']).strip()
            
            mapa_beneficios[c_key] = {
                "texto": str(r.get('BENEFICIOS', '')),
                "link": str(r.get('ENLACE', ''))
            }
    except Exception as e:
        pass # Si el archivo no está, simplemente no muestra beneficios extra
    
    # Cabecera de la tabla re-escalada
    pdf.set_font('Arial', 'B', 8); pdf.set_fill_color(240, 240, 240); pdf.set_text_color(*NEGRO)
    pdf.cell(32, 10, "ASEGURADORA", 1, 0, 'C', fill=True)
    pdf.cell(28, 10, "PRECIO", 1, 0, 'C', fill=True)
    pdf.cell(85, 10, "BENEFICIOS ADICIONALES", 1, 0, 'C', fill=True)
    pdf.cell(45, 10, "SOLICITUD", 1, 1, 'C', fill=True)
    
    for _, row in df_resultados.iterrows():
        aseg_nombre = str(row['Aseguradora'])
        h_row = 18 # Aumentamos el alto de la fila a 18mm para que quepa el texto largo
        x_start = pdf.get_x(); y_start = pdf.get_y()
        
        # 1. ASEGURADORA (32mm) - MODO LOGO INTELIGENTE
        import os
        
        # EL CAMBIO CLAVE ESTÁ AQUÍ: Usamos 'aseg_nombre' en lugar de 'c_key'
        nombre_limpio = aseg_nombre.lower().replace('í', 'i').replace(' ', '_')
        ruta_logo = f"logo_{nombre_limpio}.png"
        
        if os.path.exists(ruta_logo):
            # w=24 es el ancho del logo, h_row es el alto de la fila (18)
            pdf.image(ruta_logo, x=x_start + 4, y=y_start + 4, w=24)
            pdf.cell(32, h_row, "", "B", 0, 'C') 
        else:
            # Plan B: Si no encuentra el logo, muestra el texto
            pdf.set_font('Arial', 'B', 9); pdf.set_text_color(*NEGRO)
            pdf.cell(32, h_row, aseg_nombre, "B", 0, 'C')
        
        # 2. PRECIO (28mm)
        x_price = pdf.get_x()
        pdf.line(x_price, y_start + h_row, x_price + 28, y_start + h_row) 
        
        tiene_campana = row.get('Tiene_Campaña', False)
        try:
            precio_actual = float(row['Precio'])
            precio_lista = float(row['Precio_Lista']) if row['Precio_Lista'] != "Consultar" else precio_actual
        except: precio_actual = 0; precio_lista = 0
            
        if tiene_campana and precio_actual < precio_lista:
            pdf.set_font('Arial', '', 8); pdf.set_text_color(*GRIS)
            txt_old = f"S/ {precio_lista:.2f}"
            w_old = pdf.get_string_width(txt_old)
            pdf.text(x_price + 4, y_start + 7, txt_old)
            pdf.set_draw_color(*GRIS)
            pdf.line(x_price + 3, y_start + 6, x_price + 5 + w_old, y_start + 6)
            
            pdf.set_font('Arial', 'B', 12); pdf.set_text_color(*AZUL)
            pdf.text(x_price + 4, y_start + 13, f"S/ {precio_actual:.2f}")
        else:
            pdf.set_font('Arial', 'B', 12); pdf.set_text_color(*NEGRO)
            try: txt_p = f"S/ {precio_actual:.2f}"
            except: txt_p = str(row['Precio'])
            pdf.set_xy(x_price, y_start)
            pdf.cell(28, h_row, txt_p, 0, 0, 'C')
            
        # 3. BENEFICIOS (85mm)
        x_ben = x_price + 28
        pdf.set_xy(x_ben, y_start + 2) 
        pdf.set_draw_color(*NEGRO)
        pdf.line(x_ben, y_start + h_row, x_ben + 85, y_start + h_row) 
        
        datos_ben = mapa_beneficios.get(aseg_nombre, {"texto": "", "link": ""})
        txt_ben = datos_ben["texto"]
        link_ben = datos_ben["link"]
        
        if txt_ben and txt_ben != "nan":
            pdf.set_font('Arial', '', 7); pdf.set_text_color(80, 80, 80)
            # multi_cell hace que el texto largo se acomode automáticamente hacia abajo
            pdf.multi_cell(85, 3.5, txt_ben, 0, 'L') 
            if link_ben and link_ben != "nan":
                pdf.set_x(x_ben)
                pdf.set_font('Arial', 'U', 7); pdf.set_text_color(*AZUL)
                pdf.cell(85, 4, "Ver legales y condiciones >", 0, 0, 'L', link=link_ben)
        else:
            pdf.set_font('Arial', 'I', 7); pdf.set_text_color(150, 150, 150)
            pdf.cell(85, h_row, "Emisión inmediata garantizada.", 0, 0, 'L')

        # 4. SOLICITUD Y BOTÓN (45mm)
        x_btn = x_ben + 85
        pdf.set_xy(x_btn, y_start)
        pdf.cell(45, h_row, "", "B", 0) 
        
        msg = f"Hola YQ, abrí mi PDF de cotización y quiero emitir mi SOAT de {aseg_nombre} a S/ {precio_actual:.2f} para la placa {placa}."
        link = f"https://wa.me/51906462225?text={msg.replace(' ', '%20')}"
        pdf.set_fill_color(*VERDE_WA)
        
        # Botón dinámico centrado
        w_btn = 38
        h_btn = 7
        y_btn = y_start + ((h_row - h_btn) / 2) 
        pdf.rect(x_btn + (45 - w_btn)/2, y_btn, w_btn, h_btn, 'F')
        pdf.set_xy(x_btn + (45 - w_btn)/2, y_btn)
        pdf.set_font('Arial', 'B', 8); pdf.set_text_color(255, 255, 255)
        pdf.cell(w_btn, h_btn, "LO QUIERO AHORA >", 0, 0, 'C', link=link)
        
        # Reset de coordenadas para la siguiente fila
        pdf.set_text_color(*NEGRO); pdf.set_draw_color(0,0,0)
        pdf.set_xy(10, y_start + h_row)

    # COBERTURAS
    pdf.ln(2) # Reducimos el salto de línea para ganar espacio
    pdf.section_title("COBERTURAS PRINCIPALES")
    coberturas = [
        ("GASTOS MEDICOS", "S/ 27,500 (5 UIT)", "Atención médica, hospitalaria y quirúrgica."),
        ("MUERTE / INVALIDEZ", "S/ 22,000 (4 UIT)", "Indemnización inmediata a beneficiarios."),
        ("INCAPACIDAD", "S/ 5,500 (1 UIT)", "Pago diario por descanso médico temporal."),
        ("SEPELIO", "S/ 5,500 (1 UIT)", "Reembolso de gastos de funeral.")
    ]
    # Reducimos la altura de las celdas de 6 a 5
    pdf.set_font('Arial', 'B', 8); pdf.set_text_color(100,100,100)
    pdf.cell(50, 5, "BENEFICIO", "B", 0, 'L'); pdf.cell(40, 5, "MONTO", "B", 0, 'L'); pdf.cell(0, 5, "DETALLE", "B", 1, 'L')
    
    for t, m, d in coberturas:
        pdf.set_font('Arial', 'B', 9); pdf.set_text_color(*AZUL)
        pdf.cell(50, 5, t, "B", 0, 'L')
        pdf.set_font('Arial', 'B', 9); pdf.set_text_color(0, 100, 0)
        pdf.cell(40, 5, m, "B", 0, 'L')
        pdf.set_font('Arial', '', 8); pdf.set_text_color(100,100,100)
        pdf.cell(0, 5, d, "B", 1, 'L')

    # --- PIE DE PÁGINA ESTILO "LETRA PEQUEÑA" (AHORRO DE ESPACIO) ---
    pdf.ln(3) 
    pdf.set_text_color(120, 120, 120); pdf.set_font('Arial', '', 7) 
    
    # Condensamos las 4 reglas en una sola línea horizontal
    pdf.cell(0, 3.5, "Las coberturas aplican para todas las compañías. | Precios incluyen IGV. | Vigencia: 24h. | Cobertura inmediata tras emisión.", 0, 1, 'L')
    
    # El Disclaimer legal en una sola línea con cursiva (Itálica)
    pdf.set_font('Arial', 'I', 7) 
    pdf.cell(0, 3.5, "Nota: Los precios mostrados son referenciales y pueden variar de acuerdo a las características exactas que indique su tarjeta de propiedad.", 0, 1, 'L')
    
    if campanas_activas_txt:
        pdf.ln(1)
        pdf.set_font('Arial', 'B', 7); pdf.set_text_color(*AZUL)
        pdf.cell(0, 3.5, f"Campaña con: {campanas_activas_txt}", 0, 1, 'L')

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 3. LÓGICA DE COTIZACIÓN (CORE)
# ==========================================
class AdministradorTarifas:
    def __init__(self, ruta_directorio_csv):
        self.ruta = ruta_directorio_csv

    def obtener_tarifario(self, aseguradora):
        archivo = f"{self.ruta}/{aseguradora.lower()}_TARIFARIO.csv"
        if os.path.exists(archivo): return pd.read_csv(archivo)
        return None

    def actualizar_precio(self, aseguradora, id_fila, nuevo_precio):
        archivo = f"{self.ruta}/{aseguradora.lower()}_TARIFARIO.csv"
        df = pd.read_csv(archivo)
        df.loc[df['ID'] == id_fila, 'Precio'] = nuevo_precio
        df.to_csv(archivo, index=False)
        return "Precio actualizado con éxito."

class SoatQuotator:
    def __init__(self):
        self.data_tarifarios = {}
        self.data_grupos = {}
        self.data_zonas = {}

    def _normalizar(self, texto):
        if pd.isna(texto) or texto == "": return ""
        t = str(texto).upper().strip()
        t = t.replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U')
        return t

    def _buscar_columna(self, df, keywords):
        if df is None: return None
        cols = df.columns.tolist()
        for k in keywords:
            if k in cols: return k
        for k in keywords:
            for c in cols:
                if k in c: return c
        return None

    def cargar_datos(self, r_rimac, r_positiva, r_pacifico, r_protecta, r_mapfre):
        nombres = ['Rimac', 'La Positiva', 'Pacífico', 'Protecta', 'Mapfre']
        rutas = [r_rimac, r_positiva, r_pacifico, r_protecta, r_mapfre]
        for nombre, ruta in zip(nombres, rutas):
            try:
                if ruta.endswith('.csv'):
                    try: df = pd.read_csv(ruta, encoding='latin-1', sep=None, engine='python')
                    except: df = pd.read_csv(ruta)
                    hojas = {nombre: df}
                else:
                    xls = pd.ExcelFile(ruta)
                    hojas = {h: pd.read_excel(xls, h) for h in xls.sheet_names}

                for nombre_hoja, df in hojas.items():
                    hoja_norm = self._normalizar(nombre_hoja)
                    if ruta.endswith('.csv'):
                        cols_str = " ".join([str(c).upper() for c in df.columns])
                        if "CIRCULA" in cols_str or "ZONA" in cols_str: hoja_norm = "ZONAS"
                        elif "MODELO" in cols_str: hoja_norm = "GRUPOS"
                        elif "PRECIO" in cols_str or "LIMA" in cols_str or "COMISION" in cols_str: hoja_norm = "TARIFARIO"

                    df.columns = [self._normalizar(c) for c in df.columns]
                    if 'ZONA' in hoja_norm: self.data_zonas[nombre] = df
                    elif 'GRUPO' in hoja_norm or 'USO' in hoja_norm or 'SEGMENTACION' in hoja_norm:
                        if nombre in self.data_grupos: self.data_grupos[nombre] = pd.concat([self.data_grupos[nombre], df], ignore_index=True)
                        else: self.data_grupos[nombre] = df
                    elif 'TARIF' in hoja_norm or 'PRECIO' in hoja_norm: 
                        self.data_tarifarios[nombre] = df
            except Exception as e:
                print(f"Error carga {nombre}: {e}")

    def obtener_clases_vehiculo(self):
        clases_encontradas = set()
        palabras_ignorar = ['TODOS', 'GENERAL', 'NAN', '0', '']
        dfs = list(self.data_tarifarios.values()) + list(self.data_grupos.values())
        for df in dfs:
            if df is None: continue
            c_clase = self._buscar_columna(df, ['CLASE', 'TIPO', 'VEHICULO'])
            if c_clase:
                raw_values = df[c_clase].dropna().astype(str).unique()
                for val in raw_values:
                    items = [x.strip() for x in re.split(r'[,/]', val)]
                    for i in items:
                        i_norm = self._normalizar(i)
                        if i_norm not in palabras_ignorar and len(i_norm) > 1:
                            clases_encontradas.add(i_norm)
        return sorted(list(clases_encontradas))

    def obtener_catalogo_vehiculos(self):
        catalogo = {}
        dfs = list(self.data_grupos.values())
        for df in dfs:
            if df is None: continue
            c_marca = self._buscar_columna(df, ['MARCA'])
            c_modelo = self._buscar_columna(df, ['MODELO', 'MODELOS'])
            if c_marca and c_modelo:
                for _, row in df.iterrows():
                    m = self._normalizar(row[c_marca])
                    mod = self._normalizar(row[c_modelo])
                    if m not in ['NAN', 'TODAS', ''] and mod not in ['NAN', 'TODOS', '']:
                        if m not in catalogo: catalogo[m] = []
                        items = [x.strip() for x in mod.replace('/', ',').split(',')]
                        for i in items:
                            if i and i not in catalogo[m]: catalogo[m].append(i)
        for m in catalogo: catalogo[m] = sorted(list(set(catalogo[m])))
        return dict(sorted(catalogo.items()))

    def _check_clase(self, val_excel, val_user):
        txt = self._normalizar(val_excel); usr = self._normalizar(val_user)
        if txt == usr: return True
        if txt in ['TODOS', 'GENERAL', 'NAN', '']: return True
        if usr == "PICK UP": return "PICK" in txt
        if usr == "CAMION": return "CAMION" in txt and "CAMIONETA" not in txt
        if usr == "STATION WAGON" and "SW" in txt: return True
        if "MOTO" in usr:
            if usr == "MOTOCICLETA" and txt == "MOTOCICLETA": return True
            if usr == "MOTOCICLETA ELECTRICA" and "ELECTRICA" in txt: return True
            if usr == "CUATRIMOTO" and "CUATRI" in txt: return True
            if usr == "TRIMOTO" and "TRIMOTO" in txt: return True
            if usr == "MOTOCICLETA" and "TRIMOTO" in txt: return False
            return False
        if usr in txt: return True
        return False

    def _check_asientos(self, val_excel, val_user):
        txt = self._normalizar(val_excel); usr = int(val_user)
        if str(usr) == txt: return True
        if txt in ['TODOS', 'GENERAL', 'NAN', '']: return True
        if '-' in txt:
            try:
                a, b = map(int, txt.split('-'))
                return a <= usr <= b
            except: pass
        if 'HASTA' in txt:
            nums = [int(s) for s in re.findall(r'\d+', txt)]
            if nums: return usr <= nums[0]
        return False

    def _detectar_grupo(self, aseguradora, marca, modelo, clase, uso_usuario):
        df_g = self.data_grupos.get(aseguradora)
        if df_g is None: return "GENERAL"
        
        c_mar = self._buscar_columna(df_g, ['MARCA'])
        c_mod = self._buscar_columna(df_g, ['MODELO', 'MODELOS'])
        c_grp = self._buscar_columna(df_g, ['GRUPO', 'SEGMENTO'])
        c_cla = self._buscar_columna(df_g, ['CLASE', 'TIPO', 'VEHICULO'])
        c_uso = self._buscar_columna(df_g, ['USO'])
        
        if not (c_mar and c_mod and c_grp): return "GENERAL"
        
        u_mar = self._normalizar(marca); u_mod = self._normalizar(modelo); u_uso = self._normalizar(uso_usuario)
        mejor_grupo = "GENERAL"
        
        for _, row in df_g.iterrows():
            r_mar = self._normalizar(row[c_mar]); r_mod = self._normalizar(row[c_mod])
            match_modelo = False
            if r_mar == u_mar:
                lista_modelos = [x.strip() for x in r_mod.replace('/', ',').split(',')]
                if u_mod in lista_modelos or "TODOS" in r_mod: match_modelo = True
            if not match_modelo: continue
            if c_cla and not self._check_clase(row[c_cla], clase): continue
            
            if c_uso:
                r_uso = self._normalizar(row[c_uso])
                usos_fila = [x.strip() for x in re.split(r'[,/]', r_uso)]
                match_uso = False
                if u_uso in usos_fila: match_uso = True
                else:
                    for u in usos_fila:
                        if u in u_uso: match_uso = True; break
                if not match_uso: continue

            raw_grp = str(row[c_grp]).upper()
            if raw_grp.endswith('.0'): raw_grp = raw_grp[:-2]
            mejor_grupo = raw_grp
            break
                
        return mejor_grupo

    def _detectar_columna_precio(self, aseguradora, departamento, columnas_tarifario):
        dep_norm = self._normalizar(departamento)
        match = get_close_matches(dep_norm, columnas_tarifario, n=1, cutoff=0.85)
        if match: return match[0]
        
        sinonimos = {'CUSCO':'CUZCO', 'MADRE DE DIOS':'M. DE DIOS', 'CALLAO':'LIMA', 'LIBERTAD':'LA LIBERTAD'}
        alt = sinonimos.get(dep_norm)
        if alt:
            match_alt = get_close_matches(alt, columnas_tarifario, n=1, cutoff=0.85)
            if match_alt: return match_alt[0]

        df_z = self.data_zonas.get(aseguradora)
        if df_z is not None:
            c_dep = self._buscar_columna(df_z, ['DEPARTAMENTO', 'REGION', 'LUGAR', 'CIRCULACION'])
            c_zona = self._buscar_columna(df_z, ['ZONA', 'RIESGO', 'NOMBRE_ZONA', 'ZONAS'])
            if c_dep and c_zona:
                for _, row in df_z.iterrows():
                    ciudades_celda = [x.strip() for x in re.split(r'[,;/-]', self._normalizar(row[c_dep]))]
                    if dep_norm in ciudades_celda:
                        zona_mapeada = self._normalizar(row[c_zona])
                        match = get_close_matches(zona_mapeada, columnas_tarifario, n=1, cutoff=0.9)
                        if match: return match[0]
        
        for col in ['PRECIO', 'COSTO', 'PRIMA', 'P.V.P']:
            if col in columnas_tarifario: return col
        return "PRECIO"

    def _buscar_campana_activa(self, aseguradora, departamento, uso, clase, modelo_user):
        try:
            df_c = None
            if os.path.exists('campanas.xlsx'):
                try: df_c = pd.read_excel('campanas.xlsx')
                except: pass
            if df_c is None and os.path.exists('campanas.csv'):
                try: df_c = pd.read_csv('campanas.csv', encoding='latin-1', sep=None, engine='python')
                except: pass
            
            if df_c is None: return None, None
            
            df_c.columns = [self._normalizar(c) for c in df_c.columns]
            c_aseg = self._buscar_columna(df_c, ['ASEGURADORA', 'COMPAÑIA'])
            c_dep = self._buscar_columna(df_c, ['DEPARTAMENTO', 'REGION'])
            c_uso = self._buscar_columna(df_c, ['USO'])
            c_clase = self._buscar_columna(df_c, ['CLASE', 'TIPO'])
            c_precio = self._buscar_columna(df_c, ['PRECIO', 'COSTO'])
            c_inicio = self._buscar_columna(df_c, ['INICIO', 'DESDE'])
            c_fin = self._buscar_columna(df_c, ['FIN', 'HASTA'])
            c_nombre = self._buscar_columna(df_c, ['NOMBRE', 'CAMPAÑA'])
            c_modelos_campana = self._buscar_columna(df_c, ['MODELOS', 'MODELO'])

            if not (c_aseg and c_uso and c_clase and c_precio and c_dep): return None, None

            for col in [c_aseg, c_dep, c_uso, c_clase]: df_c[col] = df_c[col].apply(self._normalizar)
            
            def parse_fechas(serie):
                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y']:
                    try: return pd.to_datetime(serie, format=fmt)
                    except: continue
                return pd.to_datetime(serie, errors='coerce')

            df_c[c_inicio] = parse_fechas(df_c[c_inicio])
            df_c[c_fin] = parse_fechas(df_c[c_fin])
            
            hoy = pd.Timestamp.now()
            u_aseg = self._normalizar(aseguradora); u_dep = self._normalizar(departamento); u_uso = self._normalizar(uso)
            u_cla = self._normalizar(clase); u_mod = self._normalizar(modelo_user)
            
            filtro = df_c[
                (df_c[c_aseg] == u_aseg) & (df_c[c_uso] == u_uso) &
                ((df_c[c_dep] == u_dep) | (df_c[c_dep].isin(['TODOS', 'TODAS']))) &
                (df_c[c_inicio] <= hoy) & (df_c[c_fin] >= hoy)
            ]
            
            for _, row in filtro.iterrows():
                list_clases = [x.strip() for x in re.split(r'[,/]', str(row[c_clase]))]
                match_clase = False
                if u_cla in list_clases: match_clase = True
                else:
                    for item in list_clases:
                        if self._check_clase(item, u_cla): match_clase = True; break
                
                if not match_clase: continue

                if c_modelos_campana:
                    modelos_campana = self._normalizar(row[c_modelos_campana])
                    if modelos_campana not in ['TODOS', 'TODAS', 'GENERAL', '', 'NAN']:
                        lista_modelos_ok = [x.strip() for x in re.split(r'[,/]', modelos_campana)]
                        if u_mod not in lista_modelos_ok: continue

                raw_precio = str(row[c_precio])
                clean_precio = re.sub(r'[^\d.]', '', raw_precio)
                if clean_precio:
                    nombre = row[c_nombre] if c_nombre and pd.notna(row[c_nombre]) else "Oferta Especial"
                    return float(clean_precio), nombre

        except Exception: pass
        return None, None

    def cotizar(self, departamento, uso, clase, asientos, marca, modelo):
        resultados = []
        u_dep = self._normalizar(departamento); u_uso = self._normalizar(uso); u_clase = self._normalizar(clase)
        u_mar = self._normalizar(marca); u_mod = self._normalizar(modelo)
        
        for aseguradora in ['Rimac', 'La Positiva', 'Pacífico', 'Protecta', 'Mapfre']:
            df = self.data_tarifarios.get(aseguradora)
            if df is None: continue
            
            c_uso = self._buscar_columna(df, ['USO'])
            c_clase = self._buscar_columna(df, ['CLASE', 'TIPO', 'VEHICULO', 'CATEGORIA'])
            c_asientos = self._buscar_columna(df, ['ASIENTOS'])
            c_grupo = self._buscar_columna(df, ['GRUPO', 'SEGMENTO'])
            c_obs = self._buscar_columna(df, ['OBSERVACIONES', 'NOTAS'])
            c_comision = self._buscar_columna(df, ['COMISION', '%'])
            
            grupo_target = self._detectar_grupo(aseguradora, u_mar, u_mod, u_clase, u_uso)
            col_precio_target = self._detectar_columna_precio(aseguradora, u_dep, df.columns.tolist())
            
            mejor_score = -1
            mejor_fila = None
            
            if not c_uso: continue

            for idx, row in df.iterrows():
                score = 0
                r_uso = self._normalizar(row[c_uso])
                if u_uso == r_uso: score += 1000
                elif u_uso in r_uso: score += 800
                else: continue
                
                if c_clase:
                    if self._check_clase(row[c_clase], u_clase): score += 500
                    else: continue
                
                if c_grupo:
                    r_grp = str(row[c_grupo]).upper()
                    if r_grp == grupo_target: score += 500
                    elif r_grp in ['GENERAL', 'TODOS', 'RESTO', ''] and grupo_target == 'GENERAL': score += 100
                    elif r_grp.isdigit() and str(grupo_target).isdigit() and int(r_grp) == int(grupo_target): score += 500
                    else: continue 
                
                if c_asientos:
                    if self._check_asientos(row[c_asientos], asientos): score += 200
                    else: continue

                if score > mejor_score:
                    mejor_score = score
                    mejor_fila = row
            
            precio_lista = "Consultar"
            precio_final = "Consultar"
            obs = ""
            comision_pct = 0.15
            tiene_campana = False
            
            if mejor_fila is not None:
                if col_precio_target in mejor_fila:
                    val = mejor_fila[col_precio_target]
                    if pd.notna(val):
                        try: 
                            p = float(str(val).replace(',',''))
                            precio_lista = p
                            precio_final = p
                        except: pass
                
                if c_comision and pd.notna(mejor_fila[c_comision]):
                    try: comision_pct = float(mejor_fila[c_comision])
                    except: pass
                
                if c_obs and pd.notna(mejor_fila[c_obs]): obs = str(mejor_fila[c_obs])

            precio_promo, nombre_promo = self._buscar_campana_activa(aseguradora, u_dep, uso, clase, u_mod)
            if precio_promo is not None:
                precio_final = float(precio_promo)
                obs_promo = f"🔥 {nombre_promo}"
                obs = f"{obs} | {obs_promo}" if obs else obs_promo
                tiene_campana = True

            resultados.append({
                "Aseguradora": aseguradora, "Precio_Lista": precio_lista, "Precio": precio_final,
                "Tiene_Campaña": tiene_campana, "Zona": col_precio_target, "Grupo": grupo_target,
                "Observaciones": obs, "Comision_pct": comision_pct
            })
            
        return pd.DataFrame(resultados)

# ==========================================
# 4. INTEGRACIONES (ZOho, Sheets, Email)
# ==========================================
def conectar_google_sheets():
    try:
        if "gcp_service_account" in st.secrets:
            gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
            return gc.open("historial_soat").sheet1
    except Exception as e: print(f"Error conectando a Google Sheets: {e}")
    return None

def guardar_historial_google(fecha, hora, cot_id, rol, cliente, dni, celular, email, placa, marca, modelo, uso, precio_ref, cia_min, precio_min, es_campana):
    worksheet = conectar_google_sheets()
    if worksheet:
        try: worksheet.append_row([fecha, hora, cot_id, rol, cliente, dni, celular, email, placa, marca, modelo, uso, precio_ref, cia_min, precio_min, es_campana])
        except Exception as e: print(f"Error escribiendo en Google Sheets: {e}")

def descargar_historial_google():
    worksheet = conectar_google_sheets()
    if worksheet:
        try: return pd.DataFrame(worksheet.get_all_records())
        except Exception as e: st.error(f"Error leyendo Google Sheets: {e}")
    return pd.DataFrame()

def guardar_historial_local(fecha, hora, cot_id, rol, cliente, dni, celular, email, placa, marca, modelo, uso, precio_ref, cia_min, precio_min, es_campana):
    archivo_csv = "historial_cotizaciones.csv"
    data = {
        "Fecha": [fecha], "Hora": [hora], "ID": [cot_id], "Rol": [rol], "Cliente": [cliente], "DNI_RUC": [dni], 
        "Celular": [celular], "Email": [email], "Placa": [placa], "Marca": [marca], "Modelo": [modelo], 
        "Uso": [uso], "Precio_Ref": [precio_ref], "Cia_Min": [cia_min], "Precio_Min": [precio_min], "Es_Campaña": [es_campana]
    }
    df_new = pd.DataFrame(data)
    if not os.path.exists(archivo_csv): df_new.to_csv(archivo_csv, index=False, encoding='utf-8-sig')
    else: df_new.to_csv(archivo_csv, mode='a', header=False, index=False, encoding='utf-8-sig')

def enviar_notificacion(cot_id, fecha_hora, rol, cliente, celular, placa, marca, modelo, precio_min, cia_min, dni=""):
    try:
        if "ZOHO_REFRESH_TOKEN" not in st.secrets: return False, "Error de configuración de secretos."
        url_auth = "https://accounts.zoho.com/oauth/v2/token"
        datos_auth = {
            "refresh_token": st.secrets["ZOHO_REFRESH_TOKEN"], "client_id": st.secrets["ZOHO_CLIENT_ID"],
            "client_secret": st.secrets["ZOHO_CLIENT_SECRET"], "grant_type": "refresh_token"
        }
        res_auth = requests.post(url_auth, data=datos_auth).json()
        access_token = res_auth.get("access_token")
        if not access_token: raise Exception(f"Auth failed: {res_auth}")

        url_crm = "https://www.zohoapis.com/crm/v2/Leads"
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
        payload = {"data": [{"Last_Name": cliente, "Mobile": str(celular), "Lead_Source": "Cotizador SOAT Web", "Description": f"ID Cotización: {cot_id} | Fecha: {fecha_hora} | Rol: {rol} | DNI: {dni} | Vehículo: {marca} {modelo} ({placa}) | Mejor Oferta: S/ {precio_min} ({cia_min})"}]}
        res_crm = requests.post(url_crm, headers=headers, json=payload)
        
        if res_crm.status_code in [200, 201]: return True, "Exito"
        else: raise Exception(f"CRM API error: {res_crm.text}")
    except Exception as e:
        try:
            EMAIL_PASSWORD = st.secrets.get("EMAIL_PASSWORD", "")
            if not EMAIL_PASSWORD: return False, "Falla crítica."
            msg = MIMEMultipart()
            msg['From'] = "administracion@yqcorredores.com"
            msg['To'] = "administracion@yqcorredores.com"
            msg['Subject'] = f"🔔 [RESPALDO] Nueva Cotización SOAT: {cliente} ({placa})"
            msg.attach(MIMEText(f"<h3>Nueva Cotización Generada (Respaldada)</h3><p>Error técnico CRM: {e}</p>", 'html'))
            server = smtplib.SMTP("smtppro.zoho.com", 587)
            server.starttls()
            server.login("administracion@yqcorredores.com", EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            return True, "Enviado por correo de respaldo."
        except Exception:
            return False, "Fallo absoluto."

# ==========================================
# 5. PANEL DE ADMINISTRADOR DE EXCEL
# ==========================================
def mostrar_panel_administrador():
    st.header("⚙️ Panel de Administración de Tarifas")
    st.info("💡 Haz doble clic en cualquier celda para modificarla. Usa la última fila vacía para agregar nuevas opciones.")
    DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
    aseguradoras = ["rimac", "pacifico", "mapfre", "positiva", "protecta"]
    aseguradora = st.selectbox("Selecciona la Aseguradora a editar:", aseguradoras)
    ruta_archivo = os.path.join(DIRECTORIO_ACTUAL, f"{aseguradora}.xlsx")

    if os.path.exists(ruta_archivo):
        try:
            xls = pd.ExcelFile(ruta_archivo)
            hoja_seleccionada = st.selectbox("Selecciona la hoja que deseas editar:", xls.sheet_names)
            df_hoja = pd.read_excel(ruta_archivo, sheet_name=hoja_seleccionada)
            for col in df_hoja.columns:
                if df_hoja[col].dtype == 'object': df_hoja[col] = df_hoja[col].fillna("").astype(str)
            
            df_editado = st.data_editor(df_hoja, num_rows="dynamic", use_container_width=True, key=f"editor_{aseguradora}_{hoja_seleccionada}")
            
            if st.button("💾 Guardar Cambios Definitivos", type="primary"):
                try:
                    with pd.ExcelWriter(ruta_archivo, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                        df_editado.to_excel(writer, sheet_name=hoja_seleccionada, index=False)
                    st.success(f"✅ ¡La hoja '{hoja_seleccionada}' de {aseguradora.capitalize()} se actualizó de forma segura!")
                except Exception as e: st.error(f"Error crítico al intentar guardar el archivo: {e}")
        except Exception as e: st.error(f"Error al leer el archivo Excel: {e}")
    else: st.error(f"No se encontró el archivo en: {ruta_archivo}")

# ==========================================
# 6. INTERFAZ DE USUARIO PRINCIPAL
# ==========================================
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

# --- MODO CAMALEÓN: LOGO Y TÍTULO ---
origen_url = st.query_params.get("origen", "")

if origen_url != "web":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("logo_web.png"): st.image("logo_web.png", use_container_width=True)
    st.title("COTIZACION SOAT DIGITAL")
else:
    st.write("### 🚗 Cotiza y contrata en línea:")

# --- ACCESO CORREDOR (LÓGICA INVISIBLE) ---
es_admin = (st.session_state.get("clave_admin", "") == "ADMIN2026")

if carga_exitosa:
    # --- FORMULARIO OPTIMIZADO CRO ---
    st.subheader("1. Datos del Cliente")
    
    if es_admin:
        c1_1, c1_2 = st.columns(2)
        with c1_1: nombre = st.text_input("Nombre Completo")
        with c1_2: dni = st.text_input("DNI / RUC", max_chars=11, placeholder="Solo números")
        c2_1, c2_2 = st.columns(2)
        with c2_1: placa = st.text_input("Placa", max_chars=6, placeholder="ABC1234").upper()
        with c2_2: fecha_venc = st.date_input("Vencimiento SOAT", datetime.date.today(), format="DD/MM/YYYY")
        c3_1, c3_2 = st.columns(2)
        with c3_1: celular = st.text_input("Celular / Whatsapp", max_chars=9, placeholder="Ej: 999123456")
        with c3_2: email = st.text_input("Correo Electrónico", placeholder="cliente@correo.com")
    else:
        # Modo Cliente: Máxima fricción cero
        dni = "" 
        fecha_venc = datetime.date.today() 
        c1_1, c1_2 = st.columns(2)
        with c1_1: nombre = st.text_input("Nombre Completo")
        with c1_2: placa = st.text_input("Placa", max_chars=6, placeholder="ABC1234").upper()
        c2_1, c2_2 = st.columns(2)
        with c2_1: celular = st.text_input("Celular / Whatsapp", max_chars=9, placeholder="Ej: 999123456")
        with c2_2: email = st.text_input("Correo Electrónico", placeholder="cliente@correo.com")

    st.markdown("---")
    st.subheader("2. Datos del Vehículo")
    
    # 1. CARGAMOS TU BASE MAESTRA (catalogo_vehiculos.csv)
    try:
        df_vehiculos = pd.read_csv('catalogo_vehiculos.csv', sep=';', encoding='utf-8-sig')
        df_vehiculos.columns = df_vehiculos.columns.str.strip().str.upper()
        
        # Limpieza incluyendo la columna USO
        for col in ['MARCA', 'MODELO', 'CLASE', 'USO']:
            if col in df_vehiculos.columns:
                df_vehiculos[col] = df_vehiculos[col].astype(str).str.upper().str.strip()
                
        lista_marcas_maestra = sorted(df_vehiculos['MARCA'].dropna().unique().tolist())
    except Exception as e:
        st.error(f"⚠️ Error leyendo catalogo_vehiculos.csv: {e}")
        df_vehiculos = pd.DataFrame(columns=['MARCA', 'MODELO', 'CLASE', 'ASIENTOS', 'USO'])
        lista_marcas_maestra = lista_marcas 
        
    c1, c2 = st.columns(2)
    
    # 2. LÓGICA DE EXTRACCIÓN (Procesamos la columna 2 primero)
    with c2:
        # 1. Armamos la lista con un placeholder al inicio y "OTRA MARCA" al final
        opciones_marca = ["-- Selecciona tu marca --"] + lista_marcas_maestra + ["OTRA MARCA"]
        marca = st.selectbox("🚘 Marca", opciones_marca)
        
        if marca == "-- Selecciona tu marca --":
            # Estado neutro inicial: No mostramos campos de escritura
            marca_txt = ""
            mod = st.selectbox("🚙 Modelo", ["-- Esperando marca --"])
            modelo_txt = ""
            clase_sugerida = "AUTOMÓVIL"
            asientos_sugeridos = 5
            usos_permitidos = ["PARTICULAR"]
            
        elif marca == "OTRA MARCA":
            # Plan de rescate manual
            marca_txt = st.text_input("Ingresa Marca:", placeholder="Ej: TOYOTA").upper()
            mod = st.selectbox("🚙 Modelo", ["OTRO MODELO"])
            modelo_txt = st.text_input("Especificar Modelo:", placeholder="Ej: YARIS").upper()
            clase_sugerida = "AUTOMÓVIL"
            asientos_sugeridos = 5
            usos_permitidos = ["PARTICULAR", "TAXI", "CARGA", "TRANSPORTE PERSONAL", "URBANO", "INTERPROVINCIAL", "COMERCIAL","AMBULANCIA","SERVICIO ESCOLAR"]
            
        else:
            # Flujo automatizado feliz (El cliente seleccionó una marca real)
            marca_txt = marca
            modelo_opts = sorted(df_vehiculos[df_vehiculos['MARCA'] == marca]['MODELO'].dropna().unique().tolist())
            
            # Placeholder para el modelo, seguido de los modelos reales y la opción de escape al final
            opciones_modelo = ["-- Selecciona modelo --"] + modelo_opts + ["OTRO MODELO"]
            mod = st.selectbox("🚙 Modelo", opciones_modelo)
            
            if mod == "-- Selecciona modelo --":
                modelo_txt = ""
                clase_sugerida = "AUTOMÓVIL"
                asientos_sugeridos = 5
                usos_permitidos = ["PARTICULAR"]
            elif mod == "OTRO MODELO": 
                modelo_txt = st.text_input("Especificar Modelo:", placeholder="Ej: YARIS").upper()
                clase_sugerida = "AUTOMÓVIL"
                asientos_sugeridos = 5
                usos_permitidos = ["PARTICULAR", "TAXI", "CARGA", "TRANSPORTE PERSONAL", "URBANO", "INTERPROVINCIAL", "COMERCIAL","AMBULANCIA","SERVICIO ESCOLAR"]
            else: 
                modelo_txt = mod
                try:
                    fila_veh = df_vehiculos[(df_vehiculos['MARCA'] == marca) & (df_vehiculos['MODELO'] == mod)].iloc[0]
                    clase_sugerida = str(fila_veh['CLASE']).upper()
                    asientos_sugeridos = int(float(fila_veh['ASIENTOS']))
                    
                    uso_csv = str(fila_veh.get('USO', 'PARTICULAR')).upper()
                    if uso_csv != 'NAN' and uso_csv != '':
                        usos_permitidos = [u.strip() for u in uso_csv.split(',')]
                    else:
                        usos_permitidos = ["PARTICULAR"]
                except:
                    clase_sugerida = "AUTOMÓVIL"
                    asientos_sugeridos = 5
                    usos_permitidos = ["PARTICULAR", "TAXI", "CARGA", "TRANSPORTE PERSONAL", "URBANO", "INTERPROVINCIAL", "COMERCIAL","AMBULANCIA","SERVICIO ESCOLAR"]
    # 3. INTERFAZ INTELIGENTE (Procesamos la columna 1)
    with c1:
        lista_deptos = sorted(["LIMA", "AREQUIPA", "CUSCO", "LA LIBERTAD", "LAMBAYEQUE", "PIURA", "JUNIN", "ANCASH", "ICA", "SAN MARTIN", "LORETO", "UCAYALI", "CAJAMARCA", "HUANUCO", "TACNA", "PUNO", "AYACUCHO", "MOQUEGUA", "AMAZONAS", "APURIMAC", "HUANCAVELICA", "MADRE DE DIOS", "PASCO", "TUMBES"])
        try: index_def = lista_deptos.index("LIMA")
        except: index_def = 0
        depto = st.selectbox("📍 Departamento", lista_deptos, index=index_def)
        
        # --- APLICAMOS LA LISTA FILTRADA AL SELECTOR DE USO ---
        try: idx_uso = usos_permitidos.index("PARTICULAR")
        except: idx_uso = 0
        uso = st.selectbox("📋 Uso", usos_permitidos, index=idx_uso)
    
        mapa_clases = {"AUTOMÓVIL": "AUTOMOVIL", "STATION WAGON": "SW", "CAMIONETA RURAL / SUV": "SUV", "MULTIPROPÓSITO": "MULTIPROPOSITO", "CAMIONETA PANEL": "PANEL", "CAMIONETA VAN": "VAN", "MICROBUS": "MICROBUS", "MINIBUS": "MINIBUS", "OMNIBUS": "OMNIBUS", "CAMIONETA PICK UP": "PICK UP", "CAMIÓN BARANDA / FURGÓN": "CAMION", "CAMIÓN REMOLCADOR": "REMOLCADOR", "MAQUINARIA PESADA": "MAQUINARIA PESADA", "MOTO LINEAL": "MOTOCICLETA", "MOTO ELÉCTRICA": "MOTOCICLETA ELECTRICA", "TRIMOTO": "TRIMOTO", "CUATRIMOTO": "CUATRIMOTO", "MOTO FURGONETA": "FURGONETA"}
        lista_keys = list(mapa_clases.keys())
        
        try: idx_clase = lista_keys.index(clase_sugerida)
        except: idx_clase = 0
        
        if es_admin:
            clase_display = st.selectbox("🚙 Clase", lista_keys, index=idx_clase)
            clase_interna = mapa_clases[clase_display]
            asientos = st.number_input("💺 Asientos", 1, 70, value=asientos_sugeridos)
        else:
            clase_display = lista_keys[idx_clase]
            clase_interna = mapa_clases[clase_display]
            asientos = asientos_sugeridos
            
            # --- MAGIA CRO: Condicionar el mensaje de detección ---
            if marca == "-- Selecciona tu marca --" or mod == "-- Selecciona modelo --" or mod == "-- Esperando marca --":
                st.info("🔍 Selecciona tu marca y modelo para identificar tu vehículo.")
            else:
                st.success(f"✔️ Vehículo detectado: {clase_display.title()} ({asientos} asientos)")
                
    st.markdown("<br>", unsafe_allow_html=True)
    btn_generar = st.button("🔍 GENERAR COTIZACIÓN", use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True) 
    
    if 'res' not in st.session_state: st.session_state.res = None
    if 'id' not in st.session_state: st.session_state.id = None

    if btn_generar:
        errores = []
        if not nombre: errores.append("Falta el Nombre.")
        
        # 1. Validación estricta de placa peruana
        if not placa: 
            errores.append("Falta la Placa.")
        elif not re.match(r'^([A-Z0-9]{3}\d{3}|[A-Z0-9]{2}\d{4})$', placa): 
            errores.append("⚠️ La PLACA no tiene un formato válido en Perú (Ej: ABC123 o AB1234).")
            
        if not es_admin:
            # 2. Validación estricta de celular
            if not celular or not re.match(r'^9\d{8}$', celular.strip()): 
                errores.append("📱 Ingrese un celular válido de 9 dígitos (Ej: 999123456).")
            # 3. Validación estricta de correo
            if not email or not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email.strip()): 
                errores.append("📧 Ingrese un correo electrónico real.")

        if errores:
            for e in errores: st.error(e)
        else:
            with st.spinner("Cotizando..."):
                # (Aquí sigue el código normal de pytz.timezone...)
                peru_tz = pytz.timezone('America/Lima')
                now = datetime.datetime.now(peru_tz) 
                
                df = app.cotizar(depto, uso, clase_interna, asientos, marca_txt, modelo_txt)
                if not es_admin and not df.empty: df = df[df['Aseguradora'] != 'La Positiva']
                
                st.session_state.res = df
                st.session_state.id = f"2000-{now.strftime('%m%d-%H%M')}"
                rol_actual = "ADMIN" if es_admin else "CLIENTE"
                
                min_cia, min_precio, min_campana, precio_ref = "-", 0, "NO", 0
                if not df.empty:
                    df_valid = df[df['Precio'] != "Consultar"].copy()
                    if not df_valid.empty:
                        df_valid['Precio_Num'] = pd.to_numeric(df_valid['Precio'], errors='coerce')
                        df_valid = df_valid.sort_values(by='Precio_Num', ascending=True)
                        mejor = df_valid.iloc[0]
                        min_cia, min_precio, precio_ref = mejor['Aseguradora'], float(mejor['Precio_Num']), float(mejor['Precio_Num'])
                        min_campana = "SI" if mejor['Tiene_Campaña'] else "NO"
                
                f_log, h_log, f_email = now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), now.strftime('%d/%m/%Y %I:%M %p')
                guardar_historial_local(f_log, h_log, st.session_state.id, rol_actual, nombre, dni, celular, email, placa, marca_txt, modelo_txt, uso, precio_ref, min_cia, min_precio, min_campana)
                guardar_historial_google(f_log, h_log, st.session_state.id, rol_actual, nombre, dni, celular, email, placa, marca_txt, modelo_txt, uso, precio_ref, min_cia, min_precio, min_campana)
                if not es_admin: enviar_notificacion(st.session_state.id, f_email, rol_actual, nombre, celular, placa, marca_txt, modelo_txt, min_precio, min_cia)

    df_visible = pd.DataFrame() 

if st.session_state.res is not None:
    if 'id_cotizacion_actual' not in st.session_state or st.session_state.id_cotizacion_actual != st.session_state.id:
        df_base = st.session_state.res.copy()
        st.session_state.df_editable = df_base[df_base['Precio'] != "Consultar"]
        st.session_state.id_cotizacion_actual = st.session_state.id

    df_visible = st.session_state.df_editable

    if not df_visible.empty:
        st.success(f"✅ ¡Cotización exitosa! Aquí tienes las mejores opciones para tu vehículo (Ref: {st.session_state.id})")
        
        if es_admin: 
            st.info("🔓 MODO CORREDOR ACTIVADO - Ajusta los precios u observaciones antes de generar el PDF:")
            df_visible = st.data_editor(df_visible, disabled=["Aseguradora", "Grupo", "Comision_pct", "Tiene_Campaña", "Precio_Lista"], use_container_width=True, hide_index=True, key=f"editor_rapido_{st.session_state.id}")
            st.session_state.df_editable = df_visible
            st.markdown("---") 
            
        df_visible['Precio_Num'] = pd.to_numeric(df_visible['Precio'], errors='coerce').fillna(0)
        df_visible['Comisión S/.'] = (df_visible['Precio_Num'] / 1.2154) * df_visible['Comision_pct']
        df_visible['% Com'] = df_visible['Comision_pct'].apply(lambda x: f"{x*100:.0f}%")
        
        html_rows = ""
        for _, row in df_visible.iterrows():
            tiene_promo = row['Tiene_Campaña'] and row['Precio_Lista'] != "Consultar"
            if tiene_promo:
                try:
                    p_old, p_new = float(row['Precio_Lista']), float(row['Precio'])
                    precio_cell = f"<div><span style='text-decoration:line-through; color:#999; font-size:13px;'>S/ {p_old:.2f}</span><br><span style='color:#25D366; font-weight:bold; font-size:16px;'>S/ {p_new:.2f}</span></div>" if p_new < p_old else f"<span style='color:inherit; font-weight:bold; font-size:16px;'>S/ {p_new:.2f}</span>"
                except: precio_cell = f"<span style='color:inherit; font-weight:bold; font-size:16px;'>{row['Precio']}</span>"
            else:
                try: precio_cell = f"<span style='color:inherit; font-weight:bold; font-size:16px;'>S/ {float(row['Precio']):.2f}</span>"
                except: precio_cell = f"<span style='color:inherit; font-weight:bold; font-size:16px;'>{row['Precio']}</span>"

            obs_txt = str(row['Observaciones']).replace('🔥', '').strip()
            if obs_txt == "nan": obs_txt = ""
            
            if es_admin:
                html_rows += f"<tr><td><b>{row['Aseguradora']}</b></td><td>{str(row.get('Grupo', '-'))}</td><td>{precio_cell}</td><td>{row['% Com']} (S/ {row['Comisión S/.']:.2f})</td><td>{obs_txt}</td></tr>"
            else:
                html_rows += f"<tr><td><b>{row['Aseguradora']}</b></td><td>{precio_cell}</td><td>{obs_txt}</td></tr>"

        header = "<th>ASEGURADORA</th><th>GRUPO</th><th>PRECIO</th><th>COMISIÓN</th><th>OBSERVACIONES</th>" if es_admin else "<th>ASEGURADORA</th><th>PRECIO FINAL</th><th>OBSERVACIONES</th>"

        st.markdown(f"<div class='table-container'><table class='resultado-table'><thead><tr>{header}</tr></thead><tbody>{html_rows}</tbody></table></div>", unsafe_allow_html=True)
        # --- AVISO LEGAL DE PRECIOS REFERENCIALES (SOLO CLIENTES) ---
        if not es_admin:
            st.caption("⚠️ **Nota:** Los precios mostrados son referenciales y pueden variar de acuerdo a las características exactas que indique su tarjeta de propiedad.")
        st.divider()
        
        if es_admin:
            st.subheader("Configuración del PDF e Imagen (Modo Admin)")
            st.write("Desmarca las aseguradoras que **NO** deseas incluir en el documento final:")

            opciones_aseguradoras = df_visible['Aseguradora'].tolist()
            aseguradoras_seleccionadas = [aseg for i, aseg in enumerate(opciones_aseguradoras) if st.checkbox(f"Incluir {aseg}", value=True, key=f"pdf_chk_{st.session_state.id}_{i}")]

            if not aseguradoras_seleccionadas:
                st.warning("⚠️ Debes dejar marcada al menos una aseguradora para generar los documentos.")
            else:
                df_pdf = df_visible[df_visible['Aseguradora'].isin(aseguradoras_seleccionadas)]
                if st.button("📄 Generar Documentos Finales", type="primary"):
                    with st.spinner("Generando archivos..."):
                        # Inicializamos variables por seguridad para evitar NameError
                        obs_pdf = ""
                        campanas_txt = ""
                        
                        if 'Observaciones' in df_pdf.columns:
                            obs_pdf = " / ".join(df_pdf[df_pdf['Observaciones'] != ""]['Observaciones'].astype(str).unique()).replace('🔥', '').strip()
                        if 'Tiene_Campaña' in df_pdf.columns:
                            campanas_txt = ", ".join(df_pdf[df_pdf['Tiene_Campaña'] == True]['Aseguradora'].astype(str).unique().tolist())
                            
                        dni_pdf = dni if dni else "Por confirmar"
                        
                        # Generación del PDF (Todo debe estar anidado aquí adentro)
                        pdf_bytes = crear_pdf(
                            cotizacion_nro=st.session_state.id, 
                            cliente=nombre, 
                            dni_ruc=dni_pdf, 
                            celular=celular, 
                            email=email, 
                            placa=placa, 
                            marca=marca_txt, 
                            modelo=modelo_txt, 
                            uso=uso, 
                            clase=clase_display, 
                            asientos=asientos, 
                            region=depto, 
                            fecha_vencimiento=fecha_venc.strftime('%d/%m/%Y'), 
                            df_resultados=df_pdf, 
                            observaciones_especiales=obs_pdf, 
                            campanas_activas_txt=campanas_txt
                        )
                        
                        nombre_base = f"COTISOAT_{re.sub(r'[^a-zA-Z0-9]', '', nombre)}_{placa}_{datetime.datetime.now().strftime('%d%m%y_%H%M')}"
                        png_bytes = exportar_pdf_a_png(pdf_bytes)
                        
                        st.success("✅ ¡Documentos generados!")
                        col_pdf, col_img = st.columns(2)
                        with col_pdf: st.download_button("📄 Descargar PDF", data=pdf_bytes, file_name=f"{nombre_base}.pdf", mime="application/pdf", use_container_width=True)
                        with col_img:
                            if png_bytes: st.download_button("🖼️ Descargar Imagen", data=png_bytes, file_name=f"{nombre_base}.png", mime="image/png", use_container_width=True)
        else:
            # EXPERIENCIA DEL CLIENTE (CERO FRICCIÓN)
            df_pdf = df_visible 
            
            # Inicializamos variables por seguridad
            obs_pdf = ""
            campanas_txt = ""
            
            if 'Observaciones' in df_pdf.columns:
                obs_pdf = " / ".join(df_pdf[df_pdf['Observaciones'] != ""]['Observaciones'].astype(str).unique()).replace('🔥', '').strip()
            if 'Tiene_Campaña' in df_pdf.columns:
                campanas_txt = ", ".join(df_pdf[df_pdf['Tiene_Campaña'] == True]['Aseguradora'].astype(str).unique().tolist())
            
            pdf_bytes = crear_pdf(
                cotizacion_nro=st.session_state.id, 
                cliente=nombre, 
                dni_ruc="Por confirmar", 
                celular=celular, 
                email=email, 
                placa=placa, 
                marca=marca_txt, 
                modelo=modelo_txt, 
                uso=uso, 
                clase=clase_display, 
                asientos=asientos, 
                region=depto, 
                fecha_vencimiento="Por confirmar", 
                df_resultados=df_pdf, 
                observaciones_especiales=obs_pdf, 
                campanas_activas_txt=campanas_txt
            )
            
            nombre_base = f"COTISOAT_Oficial_{re.sub(r'[^a-zA-Z0-9]', '', placa)}"
            
            # --- NUEVO MENSAJE DE WHATSAPP ---
            mensaje_wa = f"Hola YQ, acabo de cotizar mi SOAT en su web para la placa {placa}. Quisiera que un asesor me ayude a elegir la mejor opción y emitir mi póliza."
            link_gracias = f"https://yqcorredores.com/gracias-soat/?msg={mensaje_wa.replace(' ', '%20')}"

            col_acc1, col_acc2 = st.columns(2)
            with col_acc1: st.link_button("📲 CONTRATAR VÍA WHATSAPP", link_gracias, type="primary", use_container_width=True)
            with col_acc2: st.download_button("📄 DESCARGAR COTIZACIÓN", data=pdf_bytes, file_name=f"{nombre_base}.pdf", mime="application/pdf", use_container_width=True)
    else:
        st.error("No hay precios disponibles.")

# ==========================================
# 7. PIE DE PÁGINA: GUÍA INFORMATIVA Y ACCESO ADMIN
# ==========================================

# --- SECCIÓN INFORMATIVA Y DE CONFIANZA (SOLO VISTA CLIENTE) ---
if not es_admin:
    st.markdown("---")
    st.markdown("<h3 style='text-align: center; color: #212529;'>¿Cómo funciona nuestro SOAT 100% Digital?</h3><br>", unsafe_allow_html=True)
    
    col_paso1, col_paso2, col_paso3 = st.columns(3)
    with col_paso1:
        st.markdown("#### 1️⃣ Cotiza al instante")
        st.write("Ingresa la placa de tu vehículo y tus datos de contacto de forma 100% segura.")
    with col_paso2:
        st.markdown("#### 2️⃣ Compara y elige")
        st.write("Nuestro sistema consulta en tiempo real con las mejores aseguradoras del país para mostrarte tus opciones sin filtros.")
    with col_paso3:
        st.markdown("#### 3️⃣ Recibe y viaja")
        st.write("Confirma tu opción, y recibe tu SOAT electrónico oficial directamente en tu correo y WhatsApp, válido de inmediato ante cualquier autoridad.")
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Testimonios rápidos
    st.markdown("<h4 style='text-align: center; color: #212529;'>Conductores que ya confían en YQ Corredores</h4>", unsafe_allow_html=True)
    c_test1, c_test2, c_test3 = st.columns(3)
    with c_test1:
        st.info("⭐⭐⭐⭐⭐\n\n«Súper rápido y transparente. Pude ver los precios de todas las aseguradoras en una sola pantalla. Pagué y me mandaron el SOAT al WhatsApp.»\n\n**- Jorge R.**")
    with c_test2:
        st.info("⭐⭐⭐⭐⭐\n\n«Prefiero comprar aquí. Si alguna vez tengo un choque, sé que el equipo de YQ me va a contestar el teléfono para asesorarme de verdad.»\n\n**- Úrsula F.**")
    with c_test3:
        st.info("⭐⭐⭐⭐⭐\n\n«Increíble la facilidad. Hice todo desde mi celular sin papeleos. El certificado digital me llegó al instante y ya verifiqué que aparece activo.»\n\n**- Roberto C.**")

# --- PANEL VISUAL DEL ASESOR (AL FINAL DE LA PÁGINA PARA TODOS) ---
st.markdown("<br><br><br>", unsafe_allow_html=True) # Espacio grande para separarlo del contenido principal

with st.expander("🛡️ Acceso Interno YQ (Solo Empleados)"):
    # Al ponerle el key="clave_admin", se conecta automáticamente con la lógica de arriba
    st.text_input("Código de Autorización", type="password", placeholder="Ingresa clave", key="clave_admin")
    
    if es_admin:
        st.success("✅ Modo Corredor Activado. Sube al inicio para cotizar con opciones avanzadas.")
        
        if st.button("📥 DESCARGAR HISTORIAL SOAT"):
            df_historial = descargar_historial_google()
            if not df_historial.empty:
                csv = df_historial.to_csv(index=False).encode('utf-8-sig')
                st.download_button("💾 Guardar CSV", csv, f"Historial_{datetime.datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
        
        st.markdown("---")
        # El panel de administración solo se muestra si la clave es correcta
        mostrar_panel_administrador()
