import streamlit as st
import pandas as pd
import httpx
import asyncio

# Configuración de la página web
st.set_page_config(page_title="Analizador de Links de Inventario", page_icon="👓", layout="centered")

st.title("👓 Analizador Masivo de Fotos por SKU")
st.write("Sube tu archivo de Excel para verificar qué SKUs tienen imágenes rotas.")

# Componente para subir el archivo Excel
uploaded_file = st.file_uploader("Elige tu archivo Excel (.xlsx)", type=["xlsx"])


# Función asíncrona para verificar un link rápidamente (con simulación de navegador)
async def verificar_url(client, url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        # Intento 1: HEAD (rápido)
        response = await client.head(url, headers=headers, timeout=3.0, follow_redirects=True)
        if response.status_code == 200:
            return True
        # Intento 2: GET (si el HEAD falló por seguridad)
        response = await client.get(url, headers=headers, timeout=3.0, follow_redirects=True)
        return response.status_code == 200
    except:
        return False

async def analizar_filas(df, columnas_links):
    skus_rotos = []
    total = len(df)
    
    # Barra de progreso visual en la web
    progreso_barra = st.progress(0)
    texto_progreso = st.empty()
    
    async with httpx.AsyncClient(verify=False) as client:
        for index, row in df.iterrows():
            current_sku = str(row.get('sku', '')).strip()
            if not current_sku or current_sku == 'nan':
                continue
                
            texto_progreso.text(f"Analizando fila {index + 1} de {total} (SKU: {current_sku})")
            progreso_barra.progress((index + 1) / total)
            
            sku_tiene_error = False
            # Revisar las 12 columnas en la fila
            for col in columnas_links:
                if col in df.columns:
                    url = str(row[col]).strip()
                    if url and url.startswith("http"):
                        exito = await verificar_url(client, url)
                        if not exito:
                            sku_tiene_error = True
                            break # Con una foto rota, marcamos el SKU y saltamos al siguiente
            
            if sku_tiene_error:
                skus_rotos.append(current_sku)
                
    texto_progreso.text("¡Análisis completado!")
    return list(set(skus_rotos)) # Eliminar duplicados por seguridad

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        
        if 'sku' not in df.columns:
            st.error("❌ El archivo debe contener obligatoriamente una columna llamada 'sku' en minúsculas.")
        else:
            # Detectar columnas que se llamen Link 1, Link 2...
            columnas_links = [f"Link {i}" for i in range(1, 13)]
            
            if st.button("🚀 Comenzar Análisis Masivo"):
                with st.spinner("Procesando enlaces en tiempo real..."):
                    # Ejecutar el análisis de forma asíncrona (ultrarrápido para +1000 links)
                    skus_finales = asyncio.run(analizar_filas(df, columnas_links))
                
                if skus_finales:
                    st.warning(f"⚠️ Se encontraron {len(skus_finales)} SKUs con enlaces rotos.")
                    
                    # Convertir la lista a texto plano para la descarga
                    txt_data = "\n".join(skus_finales)
                    
                    # Botón nativo para descargar el archivo de texto
                    st.download_button(
                        label="📥 Descargar skus_con_links_rotos.txt",
                        data=txt_data,
                        file_name="skus_con_links_rotos.txt",
                        mime="text/plain"
                    )
                else:
                    st.success("🎉 ¡Excelente! Todos los SKUs tienen sus fotos funcionando perfectamente.")
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
