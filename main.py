import os
import json
import time
import requests
import feedparser
from google import genai

# Cargar llaves desde los secretos de GitHub
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# LISTA DE FUENTES RSS
# ==========================================
FEEDS_MUSICA = [
    "https://indiehoy.com/feed/",
    "http://www.silencio.com.ar/feed/",
    "https://billboard.ar/feed/",
    "https://www.indierocks.mx/feed/",
    "https://news.google.com/rss/search?q=recitales+musica+buenos+aires+when:2d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=Movistar+Arena+OR+estadio+River+OR+Velez+recital+when:2d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=entradas+preventa+show+concierto+argentina+when:2d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=Niceto+Club+OR+Luna+Park+OR+Teatro+Flores+when:2d&hl=es-419&gl=AR&ceid=AR:es-419"
]

def obtener_noticias():
    noticias = []
    titulos_vistos = set()

    for url in FEEDS_MUSICA:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:6]:
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

def procesar_noticias_con_gemini(noticias):
    prompt = f"""
    Actúa como el editor jefe de 'Sebs.news', un medio digital de música en Buenos Aires para Instagram y TikTok.
    Analiza la lista de noticias recopiladas y selecciona exactamente las 10 noticias/novedades más relevantes para el público de Buenos Aires/Argentina.
    
    Buscá variedad de géneros (Rock Nacional, Trap/Urbano, Pop, Indie, Electrónica y Visitas Internacionales) y tipos de noticias (sold outs, anuncios, preventas/precios, lanzamientos).

    Para cada una de las 10 opciones, asigna el mejor formato de redes:
    - REEL / TIKTOK: Noticia bomba, sold out, confirmación express o urgencia.
    - CARRUSEL: Precios de entradas, fechas de preventa, tarjetas o guías paso a paso.
    - POST ÚNICO / STORY: Lanzamiento importante, foto histórica o hito relevante.

    Noticias candidatas:
    {json.dumps(noticias, ensure_ascii=False, indent=2)}

    Devuelve un reporte conciso y directo con esta estructura por cada noticia:

    [Número]. 📌 [TITULAR IMPACTANTE]
    🎬 Formato: [Reel/TikTok / Carrusel / Post Único]
    💡 Por qué: [Explicación breve en 1 línea]
    ✍️ Idea de contenido:
    - Hook / Placa 1: ...
    - Info clave: ...
    - CTA: ...
    🔗 Fuente: [Link]
    -----------------------------------
    """

    # Modelos de respaldo en orden de prioridad
    modelos = [
        'gemini-2.5-flash',
        'gemini-2.0-flash',
        'gemini-1.5-flash',
        'gemini-2.5-pro'
    ]

    for modelo in modelos:
        try:
            print(f"🧠 Consultando con modelo: {modelo}...")
            response = client.models.generate_content(
                model=modelo,
                contents=prompt,
            )
            if response and response.text:
                print(f"✅ Respuesta exitosa con {modelo}")
                return response.text
        except Exception as e:
            print(f"⚠️ Modelo {modelo} no disponible o saturado: {e}")
            time.sleep(2) # Espera 2 segundos antes de probar el siguiente modelo

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
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            print(f"❌ Error Telegram ({res.status_code}): {res.text}")
        else:
            print(f"✅ Parte {i+1}/{len(partes)} enviada con éxito a Telegram.")

if __name__ == "__main__":
    print("🔎 Rastreando múltiples fuentes...")
    noticias = obtener_noticias()
    print(f"Total de noticias recopiladas: {len(noticias)}")
    
    print("🧠 Generando el TOP 10...")
    reporte = procesar_noticias_con_gemini(noticias)
    
    if reporte:
        print("📱 Enviando reporte a Telegram...")
        enviar_telegram(f"🗞️ MESA DE REDACCIÓN (TOP 10) - SEBS.NEWS\n\n{reporte}")
        print("¡Proceso completado con éxito!")
    else:
        print("❌ No se pudo generar el reporte tras probar todos los modelos.")
