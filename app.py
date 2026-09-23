import streamlit as st
import pandas as pd
import httpx
from concurrent.futures import ThreadPoolExecutor

# Configuración de la página web
st.set_page_config(page_title="Analizador de Links de Inventario", page_icon="👓", layout="centered")

st.title("👓 Analizador Masivo de Fotos por SKU")
st.write("Sube tu archivo de Excel para verificar qué SKUs tienen imágenes rotas.")

# Componente para subir el archivo Excel
uploaded_file = st.file_uploader("Elige tu archivo Excel (.xlsx)", type=["xlsx"])

# Función limpia para verificar un link físico (Simula navegador Chrome)
def verificar_url_sync(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    # Usamos httpx en modo síncrono tradicional con verificación SSL desactivada
    with httpx.Client(verify=False, timeout=4.0) as client:
        try:
            # Intento 1: HEAD (rápido)
            response = client.head(url, headers=headers, follow_redirects=True)
            if response.status_code == 200:
                return True
            # Intento 2: GET (por si el servidor bloquea solicitudes HEAD)
            response = client.get(url, headers=headers, follow_redirects=True)
            return response.status_code == 200
        except:
            return False

# Función encargada de revisar una fila completa (Revisa sus 12 columnas de links)
def analizar_fila_individual(row, columnas_links):
    current_sku = str(row.get('sku', '')).strip()
    
    if not current_sku or current_sku.lower() == 'nan':
        return None
        
    for col in columnas_links:
        if col in row:
            url = str(row[col]).strip()
            if url and url.startswith("http"):
                # Si el link falla, marcamos el SKU como roto de inmediato
                if not verificar_url_sync(url):
                    return current_sku
    return None

if uploaded_file is not None:
    try:
        # Cargar tabla
        df = pd.read_excel(uploaded_file)
        
        if 'sku' not in df.columns:
            st.error("❌ El archivo debe contener obligatoriamente una columna llamada 'sku' en minúsculas.")
        else:
            columnas_links = [f"Link {i}" for i in range(1, 13)]
            
            if st.button("🚀 Comenzar Análisis Masivo"):
                skus_rotos = []
                total = len(df)
                
                # Elementos visuales de carga
                progreso_barra = st.progress(0)
                texto_progreso = st.empty()
                
                # Convertir filas de Pandas a diccionarios para procesarlas rápido en hilos
                filas_dict = df.to_dict(orient='records')
                
                # Ejecutar consultas en paralelo usando hilos nativos seguros (Máximo 15 conexiones simultáneas)
                with ThreadPoolExecutor(max_workers=15) as executor:
                    resultados = []
                    
                    # Lanzar todas las filas al procesador
                    for fila in filas_dict:
                        resultados.append(executor.submit(analizar_fila_individual, fila, columnas_links))
                    
                    # Monitorear el progreso en tiempo real para la pantalla del usuario
                    for index, item in enumerate(resultados):
                        sku_detectado = item.result()
                        if sku_detectado:
                            skus_rotos.append(sku_detectado)
                            
                        # Actualizar interfaz dinámica
                        texto_progreso.text(f"Procesando fila {index + 1} de {total}...")
                        progreso_barra.progress((index + 1) / total)
                
                texto_progreso.text("¡Análisis completado con éxito!")
                
                # Filtrar la lista final eliminando valores vacíos o duplicados
                skus_finales = list(set([s for s in skus_rotos if s]))
                
                if skus_finales:
                    st.warning(f"⚠️ Se encontraron {len(skus_finales)} SKUs con imágenes rotas.")
                    
                    # Generar reporte de texto plano
                    txt_data = "\n".join(skus_finales)
                    
                    st.download_button(
                        label="📥 Descargar skus_con_links_rotos.txt",
                        data=txt_data,
                        file_name="skus_con_links_rotos.txt",
                        mime="text/plain"
                    )
                else:
                    st.success("🎉 ¡Excelente! Absolutamente todos los SKUs tienen sus fotos en línea.")
                    
    except Exception as e:
        st.error(f"Error técnico al procesar el documento: {e}")
