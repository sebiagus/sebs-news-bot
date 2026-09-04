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
    # Tomamos la hora de Argentina (UTC-3) y le sumamos exactamente 1 día
    ahora = datetime.now(timezone(timedelta(hours=-3)))
    manana = ahora + timedelta(days=1)
    return f"{manana.day} de {MESES[manana.month - 1]}"

def generar_efemerides(fecha_manana):
    prompt = f"""
    Actúa como el editor de contenido de 'Sebs.news' (medio digital de música en Buenos Aires para Instagram y TikTok).
    El objetivo es preparar con anticipación el contenido para MAÑANA: {fecha_manana}.

    Identifica exactamente 2 o 3 efemérides musicales destacadas ocurridas un {fecha_manana}:
    1. HITO PRINCIPAL (ARGENTINA): Prioridad absoluta a Rock Nacional (Charly García, Luis Alberto Spinetta, Soda Stereo/Cerati, Los Redondos, Sumo, Fito Páez, Calamaro, Babasónicos, etc.) o hitos de la escena urbana argentina (Duki, Wos, etc.).
    2. HITO INTERNACIONAL: Leyendas de la música mundial (The Beatles, Queen, David Bowie, Michael Jackson, Daft Punk, Nirvana, etc.).

    Devuelve un reporte listo para Telegram optimizado para armar el contenido con tiempo:

    🗓️ *EFEMÉRIDES PARA MAÑANA - {fecha_manana.upper()}*
    _(Para preparar placas / Stories / Reels con anticipación)_

    🎸 *1. [TÍTULO DEL HITO NACIONAL / AÑO]*
    📖 *¿Qué pasó?:* [Explicación concisa y atrapante de 2 líneas]
    📲 *Idea para contenido de mañana:*
    - 🎵 *Audio / Canción sugerida:* [Tema exacto para musicalizar]
    - 🗳️ *Consigna / Debate:* [Pregunta o encuesta para que los seguidores interactúen]

    🌍 *2. [TÍTULO DEL HITO INTERNACIONAL / AÑO]*
    📖 *¿Qué pasó?:* [Explicación concisa]
    📲 *Idea para contenido:*
    - 🎵 *Audio sugerido:* [Tema]
    - 🗳️ *Consigna:* [Pregunta rápida]
    """

    modelos = ['gemini-3.6-flash', 'gemini-3.1-pro-preview']
    for modelo in modelos:
        for intento in range(2):
            try:
                print(f"🧠 Consultando efemérides para mañana con {modelo}...")
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
    print(f"📅 Generando efemérides anticipadas para mañana: {fecha_manana}...")
    
    reporte = generar_efemerides(fecha_manana)
    
    if reporte:
        print("📱 Enviando a Telegram...")
        enviar_telegram(reporte)
        print("🎉 ¡Efemérides del día siguiente enviadas con éxito!")
    else:
        print("❌ No se pudieron generar las efemérides.")
