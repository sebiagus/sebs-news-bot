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

def obtener_fecha_hoy_texto():
    ahora = datetime.now(timezone(timedelta(hours=-3))) # Hora Argentina UTC-3
    return f"{ahora.day} de {MESES[ahora.month - 1]}"

def generar_efemerides(fecha_hoy):
    prompt = f"""
    Actúa como el historiador y editor de contenido de 'Sebs.news' (medio digital de música en Buenos Aires).
    Hoy es {fecha_hoy}.

    "Identifica exactamente 4 o 5 efemérides musicales destacadas (3 de Argentina/Urbano/Rock Nacional y 2 Internacionales) ocurridas un {fecha_hoy}:
    1. HITO PRINCIPAL (ARGENTINA): Prioridad absoluta a Rock Nacional (Charly, Spinetta, Soda Stereo/Cerati, Los Redondos, Sumo, Fito Páez, Calamaro, etc.) o escena urbana argentina (hitos de Duki, Wos, etc.).
    2. HITO INTERNACIONAL: Leyendas de la música mundial (The Beatles, Queen, Bowie, Michael Jackson, Daft Punk, Nirvana, etc.).

    Devuelve un reporte listo para Telegram con ideas claras para contenido en redes (Stories / Reels / Placas):

    🗓️ *EFEMÉRIDES MUSICALES DEL DÍA - {fecha_hoy.upper()}*

    🎸 *1. [TÍTULO DEL HITO NACIONAL / AÑO]*
    📖 *¿Qué pasó?:* [Explicación concisa y atrapante de 2 líneas]
    📲 *Idea para Story / Reel:*
    - 🎵 *Audio / Canción sugerida:* [Tema exacto]
    - 🗳️ *Sticker / Consigna de debate:* [Pregunta o encuesta para que los seguidores interactúen]

    🌍 *2. [TÍTULO DEL HITO INTERNACIONAL / AÑO]*
    📖 *¿Qué pasó?:* [Explicación concisa]
    📲 *Idea para Story:*
    - 🎵 *Audio sugerido:* [Tema]
    - 🗳️ *Consigna:* [Pregunta rápida]
    """

    modelos = ['gemini-3.6-flash', 'gemini-3.1-pro-preview']
    for modelo in modelos:
        for intento in range(2):
            try:
                print(f"🧠 Consultando efemérides con {modelo}...")
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
    fecha_hoy = obtener_fecha_hoy_texto()
    print(f"📅 Generando efemérides para el {fecha_hoy}...")
    
    reporte = generar_efemerides(fecha_hoy)
    
    if reporte:
        print("📱 Enviando a Telegram...")
        enviar_telegram(reporte)
        print("🎉 ¡Efemérides enviadas con éxito!")
    else:
        print("❌ No se pudieron generar las efemérides.")
