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

# Fuentes orientadas a velocidad (Ticketeras, Productoras y Google News en tiempo real)
FEEDS_FLASH = [
    # Radares de Google News por inmediatez (when:1h para captar lo que salió hace minutos)
    "https://news.google.com/rss/search?q=AllAccess+OR+EntradaUno+OR+Ticketek+OR+Passline+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=DF+Entertainment+OR+PopArt+OR+Move+Concerts+OR+Dale+Play+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=Movistar+Arena+OR+estadio+River+OR+Velez+recital+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=nueva+fecha+OR+sold+out+OR+anuncia+show+buenos+aires+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    # Medios rápidos
    "https://billboard.ar/feed/",
    "https://indiehoy.com/feed/"
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
    ultimos = list(vistos)[-250:]
    with open(MEMORIA_FILE, "w", encoding="utf-8") as f:
        json.dump(ultimos, f, ensure_ascii=False, indent=2)

def obtener_noticias_nuevas(vistos):
    nuevas = []
    for url in FEEDS_FLASH:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:6]:
                link = entry.link.strip()
                if link not in vistos:
                    vistos.add(link)
                    nuevas.append({
                        "titulo": entry.title.strip(),
                        "link": link,
                        "resumen": entry.get("summary", "")[:250]
                    })
        except Exception as e:
            print(f"⚠️ Error feed {url}: {e}")
    return nuevas

def evaluar_urgencia(noticias_nuevas):
    if not noticias_nuevas:
        return None

    prompt = f"""
    Actúa como el editor de alertas de 'Sebs.news' (música en Buenos Aires / Argentina).
    Analiza esta lista de noticias recién detectadas.
    
    ¿Qué califica como ALERTA (debe avisar ya)?:
    - Anuncio de nueva fecha o nuevo recital (Movistar Arena, River, Vélez, Niceto, Estadio Obras, etc.).
    - Información de entradas: salida a la venta, preventa bancaria, precios o sold out.
    - Confirmación oficial de gira o visita internacional en Argentina.
    - Cancelación o cambio de fecha de un recital.

    ¿Qué IGNORAR? (No es urgente):
    - Críticas de discos, notas retrospectivas, efemérides o lanzamientos de singles sin anuncio de show.

    Noticias a evaluar:
    {json.dumps(noticias_nuevas, ensure_ascii=False, indent=2)}

    INSTRUCCIÓN:
    - Si NO hay nada de esto, responde estrictamente: NADA
    - Si hay una noticia que califique, arma el reporte flash para Telegram:

    🚨 *¡ALERTA FLASH - SEBS.NEWS!* 🚨

    💣 *Qué pasó:* [Título directo del hecho]
    ⏱️ *Lugar y Fecha:* [Si se conoce]
    💳 *Entradas:* [Detalle de preventa / tickitera / precios]

    🎬 *Guión Express para Reel/TikTok (15s):*
    - Hook: "[Gancho de 3 seg de alta energía]"
    - Cuerpo: "[Dato al hueso]"
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
            print(f"⚠️ Error {modelo}: {e}")
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
    print("⚡ Escaneo rápido Flash...")
    vistos = cargar_memoria()
    nuevas = obtener_noticias_nuevas(vistos)
    print(f"Noticias nuevas encontradas: {len(nuevas)}")

    if nuevas:
        alerta = evaluar_urgencia(nuevas)
        if alerta and "NADA" not in alerta.upper():
            print("🚨 ¡Alerta confirmada! Enviando a Telegram...")
            enviar_telegram(alerta)
        else:
            print("😴 Novedades menores, sin urgencias.")
        
        guardar_memoria(vistos)
    else:
        print("😴 Sin novedades en la red.")
