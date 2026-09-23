import streamlit as st
import pandas as pd
import httpx
from concurrent.futures import ThreadPoolExecutor

# Configuración de la página web
st.set_page_config(page_title="Analizador Universal de Inventario", page_icon="👓", layout="centered")

st.title("👓 Analizador Inteligente de Fotos por SKU")
st.write("Sube cualquier Excel. El sistema detectará automáticamente el SKU y todas las columnas con enlaces.")

# Componente para subir el archivo Excel
uploaded_file = st.file_uploader("Elige tu archivo Excel (.xlsx)", type=["xlsx"])

# Función para verificar un link físico (Simula navegador Chrome)
def verificar_url_sync(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    with httpx.Client(verify=False, timeout=5.0) as client:
        try:
            # Intento 1: HEAD (Rápido)
            response = client.head(url, headers=headers, follow_redirects=True)
            if response.status_code == 200:
                return True
            # Intento 2: GET (Por si bloquean solicitudes HEAD)
            response = client.get(url, headers=headers, follow_redirects=True)
            return response.status_code == 200
        except:
            return False

# Función encargada de revisar una fila buscando enlaces de forma dinámica
def analizar_fila_inteligente(row, columna_sku):
    # Extraer el SKU de forma limpia
    current_sku = str(row.get(columna_sku, '')).strip()
    if current_sku.endswith('.0'):
        current_sku = current_sku[:-2]
        
    if not current_sku or current_sku.lower() == 'nan' or current_sku == '':
        return None
        
    sku_tiene_error = False
    
    # Revisar absolutamente todas las celdas de la fila de forma dinámica
    for clave, valor in row.items():
        # Ignorar la columna que ya sabemos que es el SKU
        if clave == columna_sku:
            continue
            
        url = str(valor).strip()
        # Si la celda contiene un enlace real, la analizamos sin importar el nombre de la columna
        if url and url.lower() != 'nan' and url.startswith("http"):
            if not verificar_url_sync(url):
                sku_tiene_error = True
                break # Con una foto rota marcamos el SKU y pasamos al siguiente
                
    if sku_tiene_error:
        return current_sku
    return None

if uploaded_file is not None:
    try:
        # Cargamos el Excel completo
        df = pd.read_excel(uploaded_file)
        
        # 1. DETECCIÓN INTELIGENTE DE LA COLUMNA SKU
        columna_sku_detectada = None
        # Lista de nombres comunes que podría tener la columna SKU
        nombres_comunes_sku = ['sku', 'modelo', 'model', 'count', 'id', 'codigo', 'item']
        
        # Buscar si alguna columna coincide con los nombres comunes
        for col in df.columns:
            if str(col).strip().lower() in nombres_comunes_sku:
                columna_sku_detectada = col
                break
                
        # Si no coincide con ningún nombre común, asumimos que es la primera columna del Excel
        if not columna_sku_detectada and len(df.columns) > 0:
            columna_sku_detectada = df.columns[0]
            
        if not columna_sku_detectada:
            st.error("❌ No se pudo determinar la columna del SKU. Asegúrate de que el Excel tenga datos.")
        else:
            st.info(f"🔍 Sistema configurado automáticamente: Usando la columna **'{columna_sku_detectada}'** como identificador de SKU.")
            
            if st.button("🚀 Comenzar Análisis Masivo"):
                skus_rotos = []
                total = len(df)
                
                progreso_barra = st.progress(0)
                texto_progreso = st.empty()
                
                # Convertir a lista de diccionarios para procesamiento rápido en paralelo
                filas_dict = df.to_dict(orient='records')
                
                # Procesador multihilos controlado (10 conexiones en simultáneo)
                with ThreadPoolExecutor(max_workers=10) as executor:
                    resultados = []
                    
                    for fila in filas_dict:
                        resultados.append(executor.submit(analizar_fila_inteligente, fila, columna_sku_detectada))
                    
                    for index, item in enumerate(resultados):
                        sku_detectado = item.result()
                        if sku_detectado:
                            skus_rotos.append(sku_detectado)
                            
                        texto_progreso.text(f"Analizando fila {index + 1} de {total}...")
                        progreso_barra.progress((index + 1) / total)
                
                texto_progreso.text("¡Análisis masivo finalizado!")
                
                # Limpiar lista final eliminando duplicados
                skus_finales = list(set([s for s in skus_rotos if s]))
                
                if skus_finales:
                    st.warning(f"⚠️ Se encontraron {len(skus_finales)} SKUs con imágenes rotas.")
                    txt_data = "\n".join(skus_finales)
                    
                    st.download_button(
                        label="📥 Descargar skus_con_links_rotos.txt",
                        data=txt_data,
                        file_name="skus_con_links_rotos.txt",
                        mime="text/plain"
                    )
                else:
                    st.success("🎉 ¡Excelente! Absolutamente todos los enlaces del documento están activos.")
                    
    except Exception as e:
        st.error(f"Error general al procesar el archivo: {e}")
