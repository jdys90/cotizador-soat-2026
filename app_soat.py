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
    pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(240, 240, 240); pdf.set_text_color(*NEGRO)
    pdf.cell(50, 10, "ASEGURADORA", 1, 0, 'C', fill=True)
    pdf.cell(50, 10, "PRECIO", 1, 0, 'C', fill=True)
    pdf.cell(90, 10, "SOLICITUD", 1, 1, 'C', fill=True)
    
    for _, row in df_resultados.iterrows():
        h_row = 12
        x_start = pdf.get_x(); y_start = pdf.get_y()
        
        pdf.set_font('Arial', '', 10); pdf.set_text_color(*NEGRO)
        pdf.cell(50, h_row, str(row['Aseguradora']), "B", 0, 'C')
        
        x_price = pdf.get_x(); y_price = pdf.get_y()
        pdf.line(x_price, y_price + h_row, x_price + 50, y_price + h_row) 
        
        tiene_campana = row.get('Tiene_Campaña', False)
        try:
            precio_actual = float(row['Precio'])
            precio_lista = float(row['Precio_Lista']) if row['Precio_Lista'] != "Consultar" else precio_actual
        except: precio_actual = 0; precio_lista = 0
            
        if tiene_campana and precio_actual < precio_lista:
            pdf.set_font('Arial', '', 9); pdf.set_text_color(*GRIS)
            txt_old = f"S/ {precio_lista:.2f}"
            w_old = pdf.get_string_width(txt_old)
            pdf.text(x_price + 8, y_price + 9, txt_old)
            pdf.set_draw_color(*GRIS)
            pdf.line(x_price + 7, y_price + 7.5, x_price + 9 + w_old, y_price + 7.5)
            pdf.set_font('Arial', 'B', 14); pdf.set_text_color(*AZUL)
            pdf.text(x_price + 12 + w_old, y_price + 9, f"S/ {precio_actual:.2f}")
        else:
            pdf.set_font('Arial', 'B', 14); pdf.set_text_color(*NEGRO)
            try: txt_p = f"S/ {precio_actual:.2f}"
            except: txt_p = str(row['Precio'])
            pdf.set_xy(x_price, y_price)
            pdf.cell(50, h_row, txt_p, 0, 0, 'C')

        pdf.set_xy(x_price + 50, y_price)
        x_btn = pdf.get_x()
        pdf.cell(90, h_row, "", "B", 0)
        msg = f"Hola YQ, abrí mi PDF de cotización y quiero emitir mi SOAT de {row['Aseguradora']} a S/ {precio_actual:.2f} para la placa {placa}."
        link = f"https://wa.me/51906462225?text={msg.replace(' ', '%20')}"
        pdf.set_fill_color(*VERDE_WA)
        pdf.rect(x_btn + 15, y_start + 3, 60, 8, 'F')
        pdf.set_xy(x_btn + 15, y_start + 3)
        pdf.set_font('Arial', 'B', 9); pdf.set_text_color(255, 255, 255)
        pdf.cell(60, 8, "LO QUIERO AHORA >", 0, 0, 'C', link=link)
        pdf.set_text_color(*NEGRO); pdf.set_draw_color(0,0,0); pdf.ln(11)

    # COBERTURAS
    pdf.ln(5)
    pdf.section_title("COBERTURAS PRINCIPALES")
    coberturas = [
        ("GASTOS MEDICOS", "S/ 27,500 (5 UIT)", "Atención médica, hospitalaria y quirúrgica."),
        ("MUERTE / INVALIDEZ", "S/ 22,000 (4 UIT)", "Indemnización inmediata a beneficiarios."),
        ("INCAPACIDAD", "S/ 5,500 (1 UIT)", "Pago diario por descanso médico temporal."),
        ("SEPELIO", "S/ 5,500 (1 UIT)", "Reembolso de gastos de funeral.")
    ]
    pdf.set_font('Arial', 'B', 8); pdf.set_text_color(100,100,100)
    pdf.cell(50, 6, "BENEFICIO", "B", 0, 'L'); pdf.cell(40, 6, "MONTO", "B", 0, 'L'); pdf.cell(0, 6, "DETALLE", "B", 1, 'L')
    
    for t, m, d in coberturas:
        pdf.set_font('Arial', 'B', 9); pdf.set_text_color(*AZUL)
        pdf.cell(50, 6, t, "B", 0, 'L')
        pdf.set_font('Arial', 'B', 9); pdf.set_text_color(0, 100, 0)
        pdf.cell(40, 6, m, "B", 0, 'L')
        pdf.set_font('Arial', '', 8); pdf.set_text_color(100,100,100)
        pdf.cell(0, 6, d, "B", 1, 'L')

    pdf.ln(8)
    pdf.set_text_color(120, 120, 120); pdf.set_font('Arial', '', 8)
    pdf.cell(0, 4, "Las coberturas principales aplican para todas las compañías.", 0, 1, 'L')
    pdf.cell(0, 4, "Precios incluyen IGV.", 0, 1, 'L')
    pdf.cell(0, 4, "Vigencia de la cotización: 24 horas.", 0, 1, 'L')
    pdf.cell(0, 4, "La cobertura inicia inmediatamente después de la emisión y pago.", 0, 1, 'L')
    
    if campanas_activas_txt:
        pdf.set_font('Arial', 'B', 8); pdf.set_text_color(*AZUL)
        pdf.cell(0, 4, f"Campaña con: {campanas_activas_txt}", 0, 1, 'L')

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

# --- ACCESO CORREDOR ---
with st.sidebar.expander("🛡️ Acceso Interno YQ"):
    codigo_admin = st.text_input("Código de Autorización", type="password", placeholder="Ingresa clave")
es_admin = (codigo_admin == "ADMIN2026")

if es_admin:
    st.sidebar.success("Modo Corredor Activado")
    if st.sidebar.button("📥 DESCARGAR HISTORIAL"):
        df_historial = descargar_historial_google()
        if not df_historial.empty:
            csv = df_historial.to_csv(index=False).encode('utf-8-sig')
            st.sidebar.download_button("💾 Guardar CSV", csv, f"Historial_{datetime.datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

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
    
    c1, c2 = st.columns(2)
    with c1:
        lista_deptos = sorted(["LIMA", "AREQUIPA", "CUSCO", "LA LIBERTAD", "LAMBAYEQUE", "PIURA", "JUNIN", "ANCASH", "ICA", "SAN MARTIN", "LORETO", "UCAYALI", "CAJAMARCA", "HUANUCO", "TACNA", "PUNO", "AYACUCHO", "MOQUEGUA", "AMAZONAS", "APURIMAC", "HUANCAVELICA", "MADRE DE DIOS", "PASCO", "TUMBES"])
        try: index_def = lista_deptos.index("LIMA")
        except: index_def = 0
        depto = st.selectbox("📍 Departamento", lista_deptos, index=index_def)
        uso = st.selectbox("📋 Uso", ["PARTICULAR", "TAXI", "CARGA", "TRANSPORTE PERSONAL", "URBANO", "INTERPROVINCIAL", "COMERCIAL","AMBULANCIA","SERVICIO ESCOLAR"])
    
    with c2:
        mapa_clases = {"AUTOMÓVIL": "AUTOMOVIL", "STATION WAGON": "SW", "CAMIONETA RURAL / SUV": "SUV", "MULTIPROPÓSITO": "MULTIPROPOSITO", "CAMIONETA PANEL": "PANEL", "CAMIONETA VAN": "VAN", "MICROBUS": "MICROBUS", "MINIBUS": "MINIBUS", "OMNIBUS": "OMNIBUS", "CAMIONETA PICK UP": "PICK UP", "CAMIÓN BARANDA / FURGÓN": "CAMION", "CAMIÓN REMOLCADOR": "REMOLCADOR", "MAQUINARIA PESADA": "MAQUINARIA PESADA", "MOTO LINEAL": "MOTOCICLETA", "MOTO ELÉCTRICA": "MOTOCICLETA ELECTRICA", "TRIMOTO": "TRIMOTO", "CUATRIMOTO": "CUATRIMOTO", "MOTO FURGONETA": "FURGONETA"}
        clase_display = st.selectbox("🚙 Clase", list(mapa_clases.keys()))
        clase_interna = mapa_clases[clase_display]

        if es_admin:
            asientos = st.number_input("💺 Asientos", 1, 70, 5)
            marca = st.selectbox("🚘 Marca", ["OTRA MARCA"] + lista_marcas)
            if marca == "OTRA MARCA":
                marca_txt = st.text_input("Ingresa Marca:").upper()
                modelo_opts = []
            else:
                marca_txt = marca
                modelo_opts = catalogo.get(marca, [])
            mod = st.selectbox("🚙 Modelo", modelo_opts + ["OTRO MODELO"])
            if mod == "OTRO MODELO" or marca == "OTRA MARCA": modelo_txt = st.text_input("Especificar Modelo:").upper()
            else: modelo_txt = mod
        else:
            # Magia CRO: Ocultamos complejidad al cliente asumiendo variables promedio
            asientos = 5
            marca_txt = "OTRA MARCA"
            modelo_txt = "OTRO MODELO"

    st.markdown("<br>", unsafe_allow_html=True)
    btn_generar = st.button("🔍 GENERAR COTIZACIÓN", use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True) 
    
    if 'res' not in st.session_state: st.session_state.res = None
    if 'id' not in st.session_state: st.session_state.id = None

    if btn_generar:
        errores = []
        if not nombre: errores.append("Falta el Nombre.")
        if not placa or len(placa) != 6 or not placa.isalnum(): errores.append("La PLACA debe tener 6 caracteres alfanuméricos.")
        if not es_admin:
            if not celular or not celular.isdigit() or len(celular) < 9: errores.append("Ingrese un celular válido.")
            if not email or "@" not in email: errores.append("Ingrese un correo válido.")

        if errores:
            for e in errores: st.error(e)
        else:
            with st.spinner("Cotizando..."):
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
                        obs_pdf = " / ".join(df_pdf[df_pdf['Observaciones'] != ""]['Observaciones'].unique()).replace('🔥', '').strip()
                        campanas_txt = ", ".join(df_pdf[df_pdf['Tiene_Campaña'] == True]['Aseguradora'].unique().tolist())
                        dni_pdf = dni if dni else "Por confirmar"
                        
                        pdf_bytes = crear_pdf(st.session_state.id, nombre, dni_pdf, celular, email, placa, marca_txt, modelo_txt, uso, clase_display, asientos, depto, fecha_venc.strftime('%d/%m/%Y'), df_pdf, obs_pdf, campanas_txt)
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
            obs_pdf = " / ".join(df_pdf[df_pdf['Observaciones'] != ""]['Observaciones'].unique()).replace('🔥', '').strip()
            campanas_txt = ", ".join(df_pdf[df_pdf['Tiene_Campaña'] == True]['Aseguradora'].unique().tolist())
            
            pdf_bytes = crear_pdf(st.session_state.id, nombre, "Por confirmar", celular, email, placa, marca_txt, modelo_txt, uso, clase_display, asientos, depto, "Por confirmar", df_pdf, obs_pdf, campanas_txt)
            nombre_base = f"COTISOAT_Oficial_{re.sub(r'[^a-zA-Z0-9]', '', placa)}"
            
            mejor_precio = df_pdf.iloc[0]['Precio'] if not df_pdf.empty else ""
            mejor_cia = df_pdf.iloc[0]['Aseguradora'] if not df_pdf.empty else ""
            mensaje_wa = f"Hola YQ, acabo de cotizar mi SOAT en su web para la placa {placa}. Me interesa la opción de {mejor_cia} por S/ {mejor_precio}."
            link_gracias = f"https://yqcorredores.com/gracias-soat/?msg={mensaje_wa.replace(' ', '%20')}"

            col_acc1, col_acc2 = st.columns(2)
            with col_acc1: st.link_button("📲 CONTRATAR VÍA WHATSAPP", link_gracias, type="primary", use_container_width=True)
            with col_acc2: st.download_button("📄 DESCARGAR COTIZACIÓN", data=pdf_bytes, file_name=f"{nombre_base}.pdf", mime="application/pdf", use_container_width=True)
    else:
        st.error("No hay precios disponibles.")

if es_admin:
    st.markdown("---")
    mostrar_panel_administrador()
