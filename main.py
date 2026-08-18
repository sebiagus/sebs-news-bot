import os
import json
import time
import socket
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from google import genai

# Timeout de seguridad para evitar cuelgues
socket.setdefaulttimeout(10)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# FUENTES EN TIEMPO REAL (ÚLTIMAS 24 HORAS)
# ==========================================
FEEDS_MUSICA = [
    # Google News filtrado a las últimas 24hs (prensa nacional en tiempo real)
    "https://news.google.com/rss/search?q=recitales+musica+buenos+aires+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=Movistar+Arena+OR+estadio+River+OR+Velez+recital+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=entradas+preventa+show+concierto+argentina+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=Niceto+Club+OR+Luna+Park+OR+Teatro+Flores+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=lanzamiento+cancion+album+musica+argentina+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    
    # Medios especializados
    "https://indiehoy.com/feed/",
    "https://billboard.ar/feed/",
    "http://www.silencio.com.ar/feed/"
]

def es_noticia_de_hoy(entry, max_horas=28):
    """Verifica si la noticia fue publicada en las últimas 24-28 horas."""
    fecha_struct = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
    
    if not fecha_struct:
        # Si no trae fecha explícita pero viene del radar 'when:1d', la dejamos pasar
        return True, "Hoy"
    
    try:
        dt_noticia = datetime.fromtimestamp(time.mktime(fecha_struct), tz=timezone.utc)
        dt_ahora = datetime.now(timezone.utc)
        diferencia = dt_ahora - dt_noticia
        
        horas = int(diferencia.total_seconds() // 3600)
        
        # Filtro estricto: descartar si tiene más de max_horas
        if diferencia <= timedelta(hours=max_horas):
            return True, f"Hace {horas} horas"
        return False, f"Vieja ({horas}h)"
    except Exception:
        return True, "Reciente"

def obtener_noticias():
    noticias = []
    titulos_vistos = set()

    for url in FEEDS_MUSICA:
        try:
            dominio = url.split('/')[2]
            parsed = feedparser.parse(url)
            
            for entry in parsed.entries[:8]:
                titulo = entry.title.strip()
                es_reciente, etiqueta_tiempo = es_noticia_de_hoy(entry)
                
                # Solo guardamos si es de las últimas 24 horas y no está repetida
                if es_reciente and (titulo.lower() not in titulos_vistos):
                    titulos_vistos.add(titulo.lower())
                    noticias.append({
                        "titulo": titulo,
                        "link": entry.link,
                        "antiguedad": etiqueta_tiempo,
                        "resumen": entry.get("summary", "")[:200]
                    })
        except Exception as e:
            print(f"⚠️ Error al leer feed {url}: {e}")
            
    return noticias

def procesar_noticias_con_gemini(noticias):
    prompt = f"""
    Actúa como el editor jefe de 'Sebs.news', un medio digital de música en Buenos Aires para Instagram y TikTok.
    Analiza la lista de noticias recopiladas (todas de las últimas 24 horas) y selecciona las 10 mejores y MÁS FRESCAS para el público de Buenos Aires/Argentina.

    REGLA FUNDAMENTAL DE FECHAS:
    - Todas las noticias deben ser rigurosamente de HOY / ÚLTIMAS 24 HORAS.
    - Descarta cualquier noticia que parezca vieja, repetida o atemporal.
    
    Buscá variedad de géneros (Rock Nacional, Trap/Urbano, Pop, Indie, Electrónica y Visitas Internacionales) y tipos de contenido (sold outs, anuncios de estadios/Arena, preventas/precios, lanzamientos).

    Para cada noticia, asigna el mejor formato de redes:
    - REEL / TIKTOK: Noticia bomba, sold out, confirmación express o urgencia.
    - CARRUSEL: Precios de entradas, fechas de preventa, tarjetas o guías paso a paso.
    - POST ÚNICO / STORY: Lanzamiento importante, foto histórica o hito relevante.

    Noticias candidatas (con su antigüedad):
    {json.dumps(noticias, ensure_ascii=False, indent=2)}

    Devuelve un reporte conciso y directo con esta estructura por cada noticia:

    [Número]. 📌 [TITULAR IMPACTANTE]
    ⏱️ [Antigüedad / Hoy] | 🎬 Formato: [Reel/TikTok / Carrusel / Post Único]
    💡 Por qué: [Explicación breve en 1 línea]
    ✍️ Idea de contenido:
    - Hook / Placa 1: ...
    - Info clave: ...
    - CTA: ...
    🔗 Fuente: [Link]
    -----------------------------------
    """

    modelos = ['gemini-3.6-flash', 'gemini-3.1-pro-preview']

    for modelo in modelos:
        for intento in range(2):
            try:
                print(f"🧠 Consultando {modelo}...")
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                print(f"⚠️ Error con {modelo}: {e}")
                time.sleep(3)

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
    print("🔎 Rastreando noticias estrictamente de las últimas 24 horas...")
    noticias = obtener_noticias()
    print(f"Total noticias frescas encontradas: {len(noticias)}")
    
    print("🧠 Filtrando el Top 10 con Gemini...")
    reporte = procesar_noticias_con_gemini(noticias)
    
    if reporte:
        print("📱 Enviando a Telegram...")
        enviar_telegram(f"🗞️ MESA DE REDACCIÓN (NOTICIAS DE HOY) - SEBS.NEWS\n\n{reporte}")
        print("🎉 ¡Completado con éxito!")
    else:
        print("❌ No se pudo generar el reporte.")
