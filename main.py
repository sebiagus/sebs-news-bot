import os
import json
import requests
import feedparser
from google import genai

# Cargar llaves desde los secretos de GitHub
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

# Fuentes RSS a monitorear
FEEDS_MUSICA = [
    "https://indiehoy.com/feed/",
    "http://www.silencio.com.ar/feed/"
]

def obtener_noticias():
    noticias = []
    for url in FEEDS_MUSICA:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:3]:
                noticias.append({
                    "titulo": entry.title,
                    "link": entry.link,
                    "resumen": entry.get("summary", "")[:250]
                })
        except Exception as e:
            print(f"Error al leer feed {url}: {e}")
    return noticias

def procesar_noticias_con_gemini(noticias):
    prompt = f"""
    Actúa como el editor jefe de 'Sebs.news', un medio digital de música en Buenos Aires para Instagram y TikTok.
    Analiza la siguiente lista de noticias recientes y selecciona las 3 más relevantes para el público de Buenos Aires.
    
    Para cada una, determina el mejor formato:
    - REEL / TIKTOK: Noticia bomba, sold out, confirmación express o urgencia.
    - CARRUSEL: Precios de entradas, fechas de preventa, tarjetas o guías paso a paso.
    - POST ÚNICO: Lanzamiento importante, foto histórica o hito relevante.

    Noticias recibidas:
    {json.dumps(noticias, ensure_ascii=False, indent=2)}

    Devuelve un reporte claro en formato Markdown listo para Telegram con esta estructura por cada noticia:
    
    📌 *[TITULAR IMPACTANTE]*
    🎬 **Formato:** [Reel/TikTok / Carrusel / Post]
    💡 **¿Por qué este formato?:** [Explicación breve]
    ✍️ **Estructura/Guión rápido:** 
    - Hook / Placa 1: ...
    - Cuerpo / Placas siguientes: ...
    - CTA: ...
    🔗 **Fuente:** [Link]
    -----------------------------------
    """

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    return response.text

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    print("🔎 Rastreando agenda...")
    noticias = obtener_noticias()
    
    print("🧠 Procesando con Gemini...")
    reporte = procesar_noticias_con_gemini(noticias)
    
    print("📱 Enviando reporte a Telegram...")
    enviar_telegram(f"🗞️ *MESA DE REDACCIÓN - SEBS.NEWS*\n\n{reporte}")
    print("¡Proceso completado!")
