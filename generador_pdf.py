from fpdf import FPDF
from datetime import datetime
import os

# COLORES CORPORATIVOS (AZUL ELECTRICO)
AZUL = (0, 102, 204)     
FONDO = (245, 250, 255)  
NEGRO = (0, 0, 0)
ROJO = (220, 50, 50)
GRIS = (120, 120, 120)
VERDE_WA = (37, 211, 102)

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

# AÑADIDO PARAMETRO dni_ruc
def crear_pdf(cotizacion_nro, cliente, dni_ruc, celular, email, placa, marca, modelo, uso, clase, asientos, region, fecha_vencimiento, df_resultados, observaciones_especiales="", campanas_activas_txt=""):
    pdf = PDF()
    pdf.add_page()
    
    # --- 1. RESUMEN ---
    pdf.section_title("RESUMEN DE SOLICITUD")
    
    pdf.set_fill_color(*FONDO)
    pdf.rect(pdf.get_x(), pdf.get_y(), 190, 42, 'F') 
    y_ini = pdf.get_y() + 5
    
    # Columna Izq
    pdf.set_xy(15, y_ini); pdf.set_text_color(*NEGRO)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "Cotización:",0,0); pdf.set_font('Arial', 'B', 11); pdf.cell(60, 6, str(cotizacion_nro),0,1)
    
    pdf.set_x(15); pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "Cliente:",0,0); pdf.set_font('Arial', '', 10); pdf.cell(60, 6, str(cliente)[:35],0,1)
    
    # NUEVO CAMPO DNI EN PDF
    pdf.set_x(15); pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "DNI/RUC:",0,0); pdf.set_font('Arial', '', 10); pdf.cell(60, 6, str(dni_ruc),0,1)
    
    if celular:
        pdf.set_x(15); pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "Celular:",0,0); pdf.set_font('Arial', '', 10); pdf.cell(60, 6, str(celular)[:20],0,1)
    
    pdf.set_x(15); pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "Placa:",0,0); pdf.set_font('Arial', 'B', 10); pdf.cell(60, 6, str(placa),0,1)

    # Columna Der
    x_der = 120
    pdf.set_xy(x_der, y_ini)
    pdf.set_font('Arial', 'B', 9); pdf.cell(32, 6, "F. Cotización:",0,0); pdf.set_font('Arial', '', 10); pdf.cell(40, 6, datetime.now().strftime('%d/%m/%Y'),0,1)
    pdf.set_xy(x_der, y_ini+6)
    pdf.set_font('Arial', 'B', 9); pdf.cell(32, 6, "Vence SOAT:",0,0); pdf.set_font('Arial', 'B', 10); pdf.cell(40, 6, str(fecha_vencimiento),0,1)
    pdf.set_xy(x_der, y_ini+12)
    pdf.set_font('Arial', 'B', 9); pdf.cell(32, 6, "Región:",0,0); pdf.set_font('Arial', '', 10); pdf.cell(40, 6, str(region),0,1)
    pdf.set_xy(x_der, y_ini+18)
    pdf.set_font('Arial', 'B', 9); pdf.cell(32, 6, "Uso:",0,0); pdf.set_font('Arial', '', 10); pdf.cell(40, 6, str(uso),0,1)
    pdf.set_xy(x_der, y_ini+24)
    pdf.set_font('Arial', 'B', 9); pdf.cell(32, 6, "Asientos:",0,0); pdf.set_font('Arial', '', 10); pdf.cell(40, 6, str(asientos),0,1)
    
    # Vehículo (Lo movemos un poco para que cuadre)
    pdf.set_xy(x_der, y_ini+30)
    pdf.set_font('Arial', 'B', 9); pdf.cell(32, 6, "Vehículo:",0,0); pdf.set_font('Arial', '', 9); pdf.cell(40, 6, f"{marca} {modelo}"[:25],0,1)

    pdf.set_y(y_ini + 45)

    # --- 2. OFERTAS ---
    pdf.section_title("OFERTAS DISPONIBLES")
    
    pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(240, 240, 240); pdf.set_text_color(*NEGRO)
    pdf.cell(50, 10, "ASEGURADORA", 1, 0, 'C', fill=True)
    pdf.cell(50, 10, "PRECIO", 1, 0, 'C', fill=True)
    pdf.cell(90, 10, "SOLICITUD", 1, 1, 'C', fill=True)
    
    for _, row in df_resultados.iterrows():
        h_row = 14
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
            
            pdf.set_font('Arial', 'B', 14); pdf.set_text_color(*ROJO)
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
        msg = f"Hola, deseo el SOAT de {row['Aseguradora']} a S/ {row['Precio']}. Placa: {placa}"
        link = f"https://wa.me/51999999999?text={msg.replace(' ', '%20')}"
        pdf.set_fill_color(*VERDE_WA)
        pdf.rect(x_btn + 15, y_start + 3, 60, 8, 'F')
        pdf.set_xy(x_btn + 15, y_start + 3)
        pdf.set_font('Arial', 'B', 9); pdf.set_text_color(255, 255, 255)
        pdf.cell(60, 8, "LO QUIERO AHORA >", 0, 0, 'C', link=link)
        
        pdf.set_text_color(*NEGRO); pdf.set_draw_color(0,0,0); pdf.ln(11)

    # --- 3. COBERTURAS ---
    pdf.ln(5)
    pdf.section_title("COBERTURAS")
    coberturas = [
        ("GASTOS MEDICOS", "S/ 27,500 (5 UIT)", "Atencion medica, hospitalaria y quirurgica."),
        ("MUERTE / INVALIDEZ", "S/ 22,000 (4 UIT)", "Indemnizacion inmediata a beneficiarios."),
        ("INCAPACIDAD", "S/ 5,500 (1 UIT)", "Pago diario por descanso medico temporal."),
        ("SEPELIO", "S/ 5,500 (1 UIT)", "Reembolso de gastos de funeral.")
    ]
    pdf.set_font('Arial', 'B', 8); pdf.set_text_color(100,100,100)
    pdf.cell(50, 6, "BENEFICIO", "B", 0, 'L'); pdf.cell(40, 6, "MONTO", "B", 0, 'L'); pdf.cell(0, 6, "DETALLE", "B", 1, 'L')
    
    for t, m, d in coberturas:
        pdf.set_font('Arial', 'B', 9); pdf.set_text_color(*AZUL)
        pdf.cell(50, 8, t, "B", 0, 'L')
        pdf.set_font('Arial', 'B', 9); pdf.set_text_color(0, 100, 0)
        pdf.cell(40, 8, m, "B", 0, 'L')
        pdf.set_font('Arial', '', 8); pdf.set_text_color(100,100,100)
        pdf.cell(0, 8, d, "B", 1, 'L')

    # --- 4. PIE ---
    pdf.ln(8)
    pdf.set_text_color(120, 120, 120) 
    pdf.set_font('Arial', '', 8)
    
    pdf.cell(0, 4, "Precios incluyen IGV.", 0, 1, 'L')
    pdf.cell(0, 4, "Vigencia de la cotización: 24 horas.", 0, 1, 'L')
    pdf.cell(0, 4, "*La cobertura inicia inmediatamente después de la emisión y pago.", 0, 1, 'L')
    
    if campanas_activas_txt:
        pdf.set_font('Arial', 'B', 8)
        pdf.set_text_color(*AZUL)
        pdf.cell(0, 4, f"Campaña con: {campanas_activas_txt}", 0, 1, 'L')

    return pdf.output(dest='S').encode('latin-1')