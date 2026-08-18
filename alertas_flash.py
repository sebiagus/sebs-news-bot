import os
import json
import socket
import requests
import feedparser
from google import genai

socket.setdefaulttimeout(10)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

MEMORIA_FILE = "vistos.json"

FEEDS_FLASH = [
    "https://news.google.com/rss/search?q=recitales+musica+buenos+aires+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=Movistar+Arena+OR+River+OR+Velez+recital+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=entradas+preventa+show+concierto+argentina+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://indiehoy.com/feed/",
    "https://billboard.ar/feed/"
]

def cargar_memoria():
    if os.path.exists(MEMORIA_FILE):
        try:
            with open(MEMORIA_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def guardar_memoria(vistos):
    # Guardamos hasta los últimos 150 links para que el archivo sea liviano
    ultimos = list(vistos)[-150:]
    with open(MEMORIA_FILE, "w", encoding="utf-8") as f:
        json.dump(ultimos, f, ensure_ascii=False, indent=2)

def obtener_noticias_nuevas(vistos):
    nuevas = []
    for url in FEEDS_FLASH:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:5]:
                link = entry.link.strip()
                if link not in vistos:
                    vistos.add(link)
                    nuevas.append({
                        "titulo": entry.title.strip(),
                        "link": link,
                        "resumen": entry.get("summary", "")[:200]
                    })
        except Exception as e:
            print(f"⚠️ Error feed {url}: {e}")
    return nuevas

def evaluar_urgencia(noticias_nuevas):
    if not noticias_nuevas:
        return None

    prompt = f"""
    Actúa como el editor en tiempo real de 'Sebs.news' (música en Buenos Aires/Argentina).
    Analiza esta lista de noticias recién detectadas en la última hora y determina si alguna es una NOTICIA BOMBA / URGENTE.

    ¿Qué califica como URGENTE?:
    - Anuncio sorpresa de estadio o venue masivo (River, Vélez, Movistar Arena, Luna Park).
    - Sold out inmediato de un artista relevante o habilitación express de nueva función.
    - Confirmación oficial de gira/visita internacional muy esperada.
    - Cancelación o reprogramación de un recital grande.

    ¿Qué NO es urgente? (ignorar):
    - Reseñas de discos, entrevistas viejas, noticias de relleno, rankings semanales o artistas muy underground sin show.

    Noticias a evaluar:
    {json.dumps(noticias_nuevas, ensure_ascii=False, indent=2)}

    INSTRUCCIÓN DE RESPUESTA:
    - Si NO hay ninguna noticia bomba/urgente, responde ÚNICAMENTE la palabra: NADA
    - Si hay una o más noticias urgentes, redacta una alerta flash para Telegram con este formato exacto:

    🚨 *¡ALERTA FLASH - SEBS.NEWS!* 🚨

    💣 *Qué pasó:* [Título directo del hecho]
    ⏱️ *Lugar y Fecha:* [Si se conoce]
    💳 *Entradas / Info Clave:* [Datos de venta, preventa o qué hacer]

    🎬 *Guión Express para Reel/TikTok (15-20s):*
    - Hook: "[Gancho de 3 seg de alta energía]"
    - Cuerpo: "[Info rápida al hueso]"
    - CTA: "[Llamado a la acción rápido]"

    🔗 *Fuente:* [Link]
    """

    modelos = ['gemini-3.6-flash', 'gemini-3.1-pro-preview']
    for modelo in modelos:
        try:
            res = client.models.generate_content(
                model=modelo,
                contents=prompt
            )
            if res and res.text:
                return res.text.strip()
        except Exception as e:
            print(f"⚠️ Error modelo {modelo}: {e}")
    return None

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload, timeout=10)

if __name__ == "__main__":
    print("⚡ Iniciando escaneo Flash...")
    vistos = cargar_memoria()
    print(f"Memoria previa: {len(vistos)} links registrados.")

    nuevas = obtener_noticias_nuevas(vistos)
    print(f"Noticias nuevas sin procesar: {len(nuevas)}")

    if nuevas:
        alerta = evaluar_urgencia(nuevas)
        if alerta and "NADA" not in alerta.upper():
            print("🚨 ¡BOMBAZO DETECTADO! Enviando alerta a Telegram...")
            enviar_telegram(alerta)
        else:
            print("😴 Sin noticias de urgencia por ahora.")
        
        guardar_memoria(vistos)
    else:
        print("😴 No hay novedades nuevas en la red.")
    
    print("⚡ Fin del escaneo flash.")
