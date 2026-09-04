import os
import json
import time
import socket
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from google import genai

# Timeout de seguridad para evitar cuelgues de red
socket.setdefaulttimeout(10)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

# Fuentes orientadas a estrenos y novedades recientes
FEEDS_LANZAMIENTOS = [
    "https://news.google.com/rss/search?q=lanzamiento+OR+estreno+OR+nuevo+single+OR+nuevo+disco+musica+argentina+when:2d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=nuevo+tema+OR+nuevo+album+OR+videoclip+musica+when:2d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://billboard.ar/feed/",
    "https://indiehoy.com/feed/",
    "https://www.indierocks.mx/feed/"
]

def obtener_estrenos():
    noticias = []
    titulos_vistos = set()

    for url in FEEDS_LANZAMIENTOS:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:8]:
                titulo = entry.title.strip()
                if titulo.lower() not in titulos_vistos:
                    titulos_vistos.add(titulo.lower())
                    noticias.append({
                        "titulo": titulo,
                        "link": entry.link,
                        "resumen": entry.get("summary", "")[:250]
                    })
        except Exception as e:
            print(f"⚠️ Error al leer feed {url}: {e}")
            
    return noticias

def procesar_radar_viernes(noticias):
    prompt = f"""
    Actúa como el curador musical de 'Sebs.news' (medio digital de Buenos Aires para Instagram y TikTok).
    Hoy es viernes de estrenos (New Music Friday). Tu objetivo es seleccionar los 5 LANZAMIENTOS MÁS RELEVANTES E IMPACTANTES de la semana, SIN ATARTE A GÉNEROS FIJOS.

    CRITERIO EDITORIAL:
    - Prioriza impacto cultural, expectativa del público, conversación en redes y calidad artística.
    - Aplica a cualquier género (Trap/Urbano, Rock Nacional, Indie, Pop, RKT, Electrónica, etc.), siempre que sea de lo más fuerte de la semana.
    - Cero relleno: cada elección debe justificar por qué la comunidad de Sebs.news tiene que escucharla.

    DISTRIBUCIÓN DE LAS 5 OPCIONES POR ROL:
    1. 👑 EL LANZAMIENTO DE LA SEMANA (El estreno con mayor peso/hype, sea single o álbum)
    2. 🇦🇷 BOMBA NACIONAL (Lo más fuerte o comentado de la escena argentina)
    3. 🔄 REGRESO O COLABORACIÓN DESTACADA (Un junte inesperado o una vuelta tras meses de silencio)
    4. 🌍 IMPACTO GLOBAL (El lanzamiento internacional más relevante de la semana)
    5. 💎 LA JOYITA DE LA SEMANA (Recomendación con criterio de autor / propuesta que vale la pena descubrir)

    Noticias candidatas recopiladas:
    {json.dumps(noticias, ensure_ascii=False, indent=2)}

    Devuelve un reporte directo para Telegram con este formato:

    💿 *RADAR DE NOVEDADES: VIERNES DE LANZAMIENTOS*
    _(Top 5 estrenos de la semana para Sebs.news)_

    👑 *1. EL LANZAMIENTO DE LA SEMANA*
    - *Artista y Obra:* [Nombre - Título (Álbum / EP / Single)]
    - *Género:* [Género real]
    - *Por qué escuchar:* [1-2 líneas directas sobre el impacto o concepto]
    - *Canción sugerida:* [Tema clave]

    🇦🇷 *2. BOMBA NACIONAL*
    - *Artista y Obra:* [Nombre - Título]
    - *Género:* [Género real]
    - *Detalle:* [Qué lo hace relevante para la escena local]
    - *Canción sugerida:* [Tema clave]

    🔄 *3. REGRESO O COLABORACIÓN DESTACADA*
    - *Artista y Obra:* [Nombre - Título]
    - *Género:* [Género real]
    - *Detalle:* [Contexto del junte o la vuelta]
    - *Canción sugerida:* [Tema clave]

    🌍 *4. IMPACTO GLOBAL*
    - *Artista y Obra:* [Nombre - Título]
    - *Género:* [Género real]
    - *Detalle:* [Hito o lanzamiento internacional]
    - *Canción sugerida:* [Tema clave]

    💎 *5. LA JOYITA DE LA SEMANA*
    - *Artista y Obra:* [Nombre - Título]
    - *Género:* [Género real]
    - *Detalle:* [Por qué merece la pena prestarle atención]
    - *Canción sugerida:* [Tema clave]

    -----------------------------------
    📲 *PROPUESTA DE CONTENIDO RÁPIDO:*
    - *Idea para video:* [Gancho / Hook de 3 segundos para Reel o carrusel de fin de semana]
    - *Consigna de debate:* [Pregunta para que comenten los seguidores]
    """

    modelos = ['gemini-3.6-flash', 'gemini-3.1-pro-preview']
    for modelo in modelos:
        for intento in range(2):
            try:
                print(f"🧠 Curando lanzamientos con {modelo} (Intento {intento + 1})...")
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
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
    print("🎧 Buscando lanzamientos de las últimas 48 horas...")
    noticias = obtener_estrenos()
    print(f"Total novedades detectadas: {len(noticias)}")
    
    print("🧠 Procesando selección curada...")
    reporte = procesar_radar_viernes(noticias)
    
    if reporte:
        print("📱 Enviando Radar de Viernes a Telegram...")
        enviar_telegram(reporte)
        print("🎉 ¡Lanzamientos enviados con éxito!")
    else:
        print("❌ No se pudo generar el reporte de lanzamientos.")
