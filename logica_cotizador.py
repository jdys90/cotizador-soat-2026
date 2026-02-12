import pandas as pd
import warnings
import re
import os
from difflib import get_close_matches
from datetime import datetime

warnings.filterwarnings('ignore')

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
                    
                    if 'ZONA' in hoja_norm: 
                        self.data_zonas[nombre] = df
                    elif 'GRUPO' in hoja_norm or 'USO' in hoja_norm or 'SEGMENTACION' in hoja_norm:
                        if nombre in self.data_grupos:
                            self.data_grupos[nombre] = pd.concat([self.data_grupos[nombre], df], ignore_index=True)
                        else:
                            self.data_grupos[nombre] = df
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
        txt = self._normalizar(val_excel)
        usr = self._normalizar(val_user)
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
        txt = self._normalizar(val_excel)
        usr = int(val_user)
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

    # --- NUEVA LÓGICA DE DETECCIÓN INTELIGENTE ---
    def _detectar_grupo(self, aseguradora, marca, modelo, clase, uso_usuario):
        df_g = self.data_grupos.get(aseguradora)
        if df_g is None: return "GENERAL"
        
        c_mar = self._buscar_columna(df_g, ['MARCA'])
        c_mod = self._buscar_columna(df_g, ['MODELO', 'MODELOS'])
        c_grp = self._buscar_columna(df_g, ['GRUPO', 'SEGMENTO'])
        c_cla = self._buscar_columna(df_g, ['CLASE', 'TIPO', 'VEHICULO'])
        c_uso = self._buscar_columna(df_g, ['USO']) # Importante leer el uso del catálogo
        
        if not (c_mar and c_mod and c_grp): return "GENERAL"
        
        u_mar = self._normalizar(marca)
        u_mod = self._normalizar(modelo)
        u_uso = self._normalizar(uso_usuario)
        
        mejor_grupo = "GENERAL"
        encontro_exacto = False
        
        for _, row in df_g.iterrows():
            r_mar = self._normalizar(row[c_mar])
            r_mod = self._normalizar(row[c_mod])
            
            # 1. Coincidencia de Marca y Modelo
            match_modelo = False
            if r_mar == u_mar:
                lista_modelos = [x.strip() for x in r_mod.replace('/', ',').split(',')]
                if u_mod in lista_modelos: match_modelo = True
                elif "TODOS" in r_mod: match_modelo = True
            
            if not match_modelo: continue

            # 2. Validación de Clase (Si existe en catálogo)
            if c_cla:
                if not self._check_clase(row[c_cla], clase): continue

            # 3. LÓGICA CLAVE: Validación de USO
            # Si el catálogo especifica un uso, debemos ver si coincide con el del usuario.
            # Si coincide -> Es un grupo especial.
            # Si NO coincide -> Ignoramos este grupo (y el sistema usará "GENERAL" al final).
            if c_uso:
                r_uso = self._normalizar(row[c_uso])
                # Chequeamos si el uso del usuario está permitido en esta fila
                # Ej: Usuario "TAXI", Fila "PARTICULAR" -> No coinciden -> Ignorar fila
                # Ej: Usuario "PARTICULAR", Fila "PARTICULAR" -> Coinciden -> Usar Grupo
                
                # Soportamos listas en el excel (Ej: "PARTICULAR, TAXI")
                usos_fila = [x.strip() for x in re.split(r'[,/]', r_uso)]
                match_uso = False
                if u_uso in usos_fila: match_uso = True
                else:
                    # Match parcial
                    for u in usos_fila:
                        if u in u_uso: match_uso = True; break
                
                if not match_uso: continue

            # Si llegamos aquí, es porque Marca, Modelo, Clase y USO coinciden.
            raw_grp = str(row[c_grp]).upper()
            if raw_grp.endswith('.0'): raw_grp = raw_grp[:-2]
            mejor_grupo = raw_grp
            encontro_exacto = True
            break # Encontramos el grupo específico para este uso
                
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

            for col in [c_aseg, c_dep, c_uso, c_clase]:
                df_c[col] = df_c[col].apply(self._normalizar)
            
            def parse_fechas(serie):
                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y']:
                    try: return pd.to_datetime(serie, format=fmt)
                    except: continue
                return pd.to_datetime(serie, errors='coerce')

            df_c[c_inicio] = parse_fechas(df_c[c_inicio])
            df_c[c_fin] = parse_fechas(df_c[c_fin])
            
            hoy = pd.Timestamp.now()
            
            u_aseg = self._normalizar(aseguradora)
            u_dep = self._normalizar(departamento)
            u_uso = self._normalizar(uso)
            u_cla = self._normalizar(clase)
            u_mod = self._normalizar(modelo_user)
            
            filtro = df_c[
                (df_c[c_aseg] == u_aseg) &
                (df_c[c_uso] == u_uso) &
                ((df_c[c_dep] == u_dep) | (df_c[c_dep].isin(['TODOS', 'TODAS']))) &
                (df_c[c_inicio] <= hoy) &
                (df_c[c_fin] >= hoy)
            ]
            
            for _, row in filtro.iterrows():
                list_clases = [x.strip() for x in re.split(r'[,/]', str(row[c_clase]))]
                match_clase = False
                if u_cla in list_clases: match_clase = True
                else:
                    for item in list_clases:
                        if self._check_clase(item, u_cla):
                            match_clase = True
                            break
                
                if not match_clase: continue

                if c_modelos_campana:
                    modelos_campana = self._normalizar(row[c_modelos_campana])
                    if modelos_campana not in ['TODOS', 'TODAS', 'GENERAL', '', 'NAN']:
                        lista_modelos_ok = [x.strip() for x in re.split(r'[,/]', modelos_campana)]
                        if u_mod not in lista_modelos_ok:
                            continue

                raw_precio = str(row[c_precio])
                clean_precio = re.sub(r'[^\d.]', '', raw_precio)
                if clean_precio:
                    nombre = row[c_nombre] if c_nombre and pd.notna(row[c_nombre]) else "Oferta Especial"
                    return float(clean_precio), nombre

        except Exception:
            pass
        return None, None

    def cotizar(self, departamento, uso, clase, asientos, marca, modelo):
        resultados = []
        u_dep = self._normalizar(departamento)
        u_uso = self._normalizar(uso)
        u_clase = self._normalizar(clase)
        u_mar = self._normalizar(marca)
        u_mod = self._normalizar(modelo)
        
        for aseguradora in ['Rimac', 'La Positiva', 'Pacífico', 'Protecta', 'Mapfre']:
            df = self.data_tarifarios.get(aseguradora)
            if df is None: continue
            
            c_uso = self._buscar_columna(df, ['USO'])
            c_clase = self._buscar_columna(df, ['CLASE', 'TIPO', 'VEHICULO', 'CATEGORIA'])
            c_asientos = self._buscar_columna(df, ['ASIENTOS'])
            c_grupo = self._buscar_columna(df, ['GRUPO', 'SEGMENTO'])
            c_obs = self._buscar_columna(df, ['OBSERVACIONES', 'NOTAS'])
            c_comision = self._buscar_columna(df, ['COMISION', '%'])
            
            # --- DETECCIÓN DE GRUPO CON USO ---
            # Pasamos u_uso para que sepa si buscar en Particular o ignorar
            grupo_target = self._detectar_grupo(aseguradora, u_mar, u_mod, u_clase, u_uso)
            
            col_precio_target = self._detectar_columna_precio(aseguradora, u_dep, df.columns.tolist())
            
            mejor_score = -1
            mejor_fila = None
            
            if not c_uso: continue

            for idx, row in df.iterrows():
                score = 0
                r_uso = self._normalizar(row[c_uso])
                
                # Match de Uso
                if u_uso == r_uso: score += 1000
                elif u_uso in r_uso: score += 800
                else: continue # Si el uso no coincide, no sirve esta tarifa
                
                # Match de Clase
                if c_clase:
                    if self._check_clase(row[c_clase], u_clase): score += 500
                    else: continue
                
                # Match de Grupo
                if c_grupo:
                    r_grp = str(row[c_grupo]).upper()
                    # 1. Match Exacto (Ej: Target=3, Row=3)
                    if r_grp == grupo_target: 
                        score += 500
                    # 2. Match Genérico (Ej: Target=GENERAL, Row=TODOS)
                    elif r_grp in ['GENERAL', 'TODOS', 'RESTO', ''] and grupo_target == 'GENERAL': 
                        score += 100
                    # 3. Match Numérico
                    elif r_grp.isdigit() and str(grupo_target).isdigit() and int(r_grp) == int(grupo_target): 
                        score += 500
                    else: 
                        continue 
                
                # Match Asientos
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
                
                if c_obs and pd.notna(mejor_fila[c_obs]):
                    obs = str(mejor_fila[c_obs])

            precio_promo, nombre_promo = self._buscar_campana_activa(aseguradora, u_dep, uso, clase, u_mod)
            if precio_promo is not None:
                precio_final = float(precio_promo)
                obs_promo = f"🔥 {nombre_promo}"
                obs = f"{obs} | {obs_promo}" if obs else obs_promo
                tiene_campana = True

            resultados.append({
                "Aseguradora": aseguradora,
                "Precio_Lista": precio_lista,
                "Precio": precio_final,
                "Tiene_Campaña": tiene_campana,
                "Zona": col_precio_target,
                "Grupo": grupo_target,
                "Observaciones": obs,
                "Comision_pct": comision_pct
            })
            
        return pd.DataFrame(resultados)