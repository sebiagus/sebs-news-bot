import os
import time
import requests
from datetime import datetime, timezone, timedelta
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", 
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

def obtener_fecha_manana_texto():
    ahora = datetime.now(timezone(timedelta(hours=-3)))
    manana = ahora + timedelta(days=1)
    return f"{manana.day} de {MESES[manana.month - 1]}"

def generar_efemerides(fecha_manana):
    prompt = f"""
    Actúa como el editor de contenido de 'Sebs.news' (medio digital de música en Buenos Aires para Instagram y TikTok).
    El objetivo es preparar con anticipación el contenido para MAÑANA: {fecha_manana}.

    Identifica exactamente 5 EFEMÉRIDES MUSICALES DESTACADAS ocurridas un {fecha_manana}.
    
    CRITERIO EDITORIAL Y VARIEDAD DE GÉNEROS:
    - Asegura diversidad sonora: no te limites al rock tradicional. Considera Rock, Urbano/Trap/RKT, Pop, Indie, Electrónica y leyendas globales.
    - Criterio de relevancia estricto: lanzamientos de álbumes históricos, singles consagratorios, recitales memorables en venues clave (Obras, River, Luna Park, estadios mundiales), hitos de charts o aniversarios de figuras indiscutidas.
    
    DISTRIBUCIÓN REQUERIDA (5 OPCIONES):
    1. Nacional: Rock / Pop / Indie Argentino
    2. Nacional: Urbano / Trap / Escena contemporánea o nuevo clásico
    3. Internacional: Rock / Indie / Alternativo
    4. Internacional: Pop / Electrónica / Hip-Hop
    5. Hito Destacado: Concierto en vivo legendario, récord histórico o aniversario redondo

    Devuelve un reporte listo para Telegram con este formato exacto:

    🗓️ *EFEMÉRIDES PARA MAÑANA - {fecha_manana.upper()}*
    _(Menú de 5 opciones para preparar placas / Stories / Reels)_

    [Número]. 📌 *[TÍTULO DEL HITO / AÑO]*
    🏷️ *Género / Escena:* [Ej: Trap Argentino / Indie Rock / Rock Nacional / Electrónica]
    📖 *¿Qué pasó?:* [Resumen atrapante en 2 líneas]
    📲 *Idea para redes:*
    - 🎵 *Audio:* [Tema recomendado para musicalizar]
    - 🗳️ *Debate / Sticker:* [Consigna o pregunta para engagement]
    -----------------------------------
    """

    modelos = ['gemini-3.6-flash', 'gemini-3.1-pro-preview']
    for modelo in modelos:
        for intento in range(2):
            try:
                print(f"🧠 Consultando 5 efemérides para mañana con {modelo}...")
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                print(f"⚠️ Error {modelo}: {e}")
                time.sleep(2)
    return None

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload, timeout=10)

if __name__ == "__main__":
    fecha_manana = obtener_fecha_manana_texto()
    print(f"📅 Buscando 5 efemérides multigénero para mañana: {fecha_manana}...")
    
    reporte = generar_efemerides(fecha_manana)
    
    if reporte:
        print("📱 Enviando reporte a Telegram...")
        enviar_telegram(reporte)
        print("🎉 ¡5 efemérides enviadas con éxito!")
    else:
        print("❌ No se pudieron generar las efemérides.")
