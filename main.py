import os
import json
import time
import socket
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from google import genai

# Timeout de seguridad para evitar cuelgues
socket.setdefaulttimeout(15)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

FEEDS_MUSICA = [
    "https://news.google.com/rss/search?q=recitales+musica+buenos+aires+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=Movistar+Arena+OR+estadio+River+OR+Velez+recital+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=entradas+preventa+show+concierto+argentina+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=Niceto+Club+OR+Luna+Park+OR+Teatro+Flores+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=lanzamiento+cancion+album+musica+argentina+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://indiehoy.com/feed/",
    "https://billboard.ar/feed/",
    "http://www.silencio.com.ar/feed/"
]

def es_noticia_de_hoy(entry, max_horas=28):
    fecha_struct = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
    if not fecha_struct:
        return True, "Hoy"
    try:
        dt_noticia = datetime.fromtimestamp(time.mktime(fecha_struct), tz=timezone.utc)
        dt_ahora = datetime.now(timezone.utc)
        diferencia = dt_ahora - dt_noticia
        horas = int(diferencia.total_seconds() // 3600)
        if diferencia <= timedelta(hours=max_horas):
            return True, f"Hace {horas}h"
        return False, f"Vieja ({horas}h)"
    except Exception:
        return True, "Reciente"

def obtener_noticias():
    noticias = []
    titulos_vistos = set()

    for url in FEEDS_MUSICA:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:6]:
                titulo = entry.title.strip()
                es_reciente, etiqueta_tiempo = es_noticia_de_hoy(entry)
                
                if es_reciente and (titulo.lower() not in titulos_vistos):
                    titulos_vistos.add(titulo.lower())
                    noticias.append({
                        "titulo": titulo,
                        "link": entry.link,
                        "antiguedad": etiqueta_tiempo,
                        "resumen": entry.get("summary", "")[:180]
                    })
        except Exception as e:
            print(f"⚠️ Error al leer feed {url}: {e}")
            
    # Acotamos a un máximo de 20 noticias para no enviar un prompt masivo a la API
    return noticias[:20]

def procesar_noticias(noticias):
    prompt = f"""
    Actúa como el editor jefe de 'Sebs.news', medio digital de música en Buenos Aires para Instagram y TikTok.
    Analiza la lista de noticias recopiladas (todas de las últimas 24 horas) y selecciona las 10 mejores y MÁS FRESCAS para el público de Buenos Aires/Argentina.

    REGLA DE FECHAS:
    - Todas las noticias deben ser rigurosamente de HOY / ÚLTIMAS 24 HORAS.
    - Descarta noticias viejas o atemporales.
    
    Formatos a asignar:
    - REEL / TIKTOK: Noticia bomba, sold out, confirmación express o urgencia.
    - CARRUSEL: Precios de entradas, fechas de preventa, tarjetas o guías paso a paso.
    - POST ÚNICO / STORY: Lanzamiento importante, foto histórica o hito relevante.

    Noticias candidatas:
    {json.dumps(noticias, ensure_ascii=False, indent=2)}

    Devuelve un reporte conciso y directo con esta estructura por cada noticia:

    [Número]. 📌 [TITULAR IMPACTANTE]
    ⏱️ [Antigüedad] | 🎬 Formato: [Reel/TikTok / Carrusel / Post Único]
    💡 Por qué: [Explicación breve en 1 línea]
    ✍️ Idea de contenido:
    - Hook / Placa 1: ...
    - Info clave: ...
    - CTA: ...
    🔗 Fuente: [Link]
    -----------------------------------
    """

    modelo = 'gemini-3.6-flash'
    pausas = [5, 15, 30]  # Esperas progresivas si hay pico de demanda (503)

    for intento in range(len(pausas) + 1):
        try:
            print(f"🧠 Consultando {modelo} (Intento {intento + 1}/{len(pausas) + 1})...")
            response = client.models.generate_content(
                model=modelo,
                contents=prompt,
            )
            if response and response.text:
                return response.text
        except Exception as e:
            print(f"⚠️ Error en intento {intento + 1}: {e}")
            if intento < len(pausas):
                tiempo_espera = pausas[intento]
                print(f"⏳ Esperando {tiempo_espera}s a que se libere la API...")
                time.sleep(tiempo_espera)

    return None

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    limite = 3800
    partes = []
    
    if len(mensaje) <= limite:
        partes.append(mensaje)
    else:
        while len(mensaje) > limite:
            corte = mensaje.rfind("-----------------------------------", 0, limite)
            if corte == -1:
                corte = mensaje.rfind("\n\n", 0, limite)
            if corte == -1:
                corte = limite
            partes.append(mensaje[:corte].strip())
            mensaje = mensaje[corte:].strip()
        if mensaje:
            partes.append(mensaje)

    for i, parte in enumerate(partes):
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": parte,
            "disable_web_page_preview": True
        }
        requests.post(url, json=payload, timeout=10)

if __name__ == "__main__":
    print("🔎 Rastreando noticias de las últimas 24 horas...")
    noticias = obtener_noticias()
    print(f"Total noticias frescas seleccionadas para procesar: {len(noticias)}")
    
    print("🧠 Procesando Top 10...")
    reporte = procesar_noticias(noticias)
    
    if reporte:
        print("📱 Enviando a Telegram...")
        enviar_telegram(f"🗞️ MESA DE REDACCIÓN (NOTICIAS DE HOY) - SEBS.NEWS\n\n{reporte}")
        print("🎉 ¡Noticias enviadas!")
    else:
        print("❌ No se pudo generar el reporte.")
