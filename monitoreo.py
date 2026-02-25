import feedparser
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import os, json, gspread
from google.oauth2.service_account import Credentials
from deep_translator import GoogleTranslator

# ---------- ID DEL SHEET CORRECTO ----------
SPREADSHEET_ID = "1KhVwAHYcwSU6h4U0GTFfFmODVy7ZgV21Q1Ahjo7aoqw"

# ---------- FUENTES ----------
FUENTES = {
    "Google Tech Global":
        "https://news.google.com/rss/search?q=technology+regulation+children+privacy+platforms&hl=en-US&gl=US&ceid=US:en",

    "Google Policy Europe":
        "https://news.google.com/rss/search?q=digital+regulation+EU+children+internet+law&hl=en-GB&gl=GB&ceid=GB:en",

    "Google Latam Tech":
        "https://news.google.com/rss/search?q=regulacion+digital+niños+internet+plataformas&hl=es-419&gl=CO&ceid=CO:es-419",

    "TechCrunch":
        "https://techcrunch.com/tag/policy/feed/",

    "The Verge Policy":
        "https://www.theverge.com/rss/policy/index.xml"
}

# ---------- PALABRAS CLAVE ----------
CLAVES = [
    "children","child","kids","minor","youth","teen",
    "privacy","data protection","platform regulation",
    "online safety","digital safety","content moderation",
    "ai regulation","screen time","parental control",
    "niños","infancia","menores","protección digital",
    "plataformas","regulación","internet","televisión"
]

# ---------- FUNCIONES TEXTO ----------
def limpiar(t):
    return " ".join(str(t).replace("\n"," ").split())

def relevante(t):
    return any(p in str(t).lower() for p in CLAVES)

def traducir(t):
    try:
        return GoogleTranslator(source="auto", target="es").translate(t)
    except:
        return t

# ---------- RECOLECTAR ----------
def recolectar():

    datos = []

    for medio, url in FUENTES.items():
        feed = feedparser.parse(url)

        for e in feed.entries:
            titulo = limpiar(e.title)

            if not relevante(titulo):
                continue

            datos.append({
                "medio": str(medio),
                "titulo_original": str(titulo),
                "titulo_es": str(traducir(titulo)),
                "link": str(e.link),
                "fecha": datetime.now(
                    ZoneInfo("America/Bogota")
                ).strftime("%Y-%m-%d %H:%M")
            })

    df = pd.DataFrame(datos)

    if not df.empty:
        df.drop_duplicates(subset=["titulo_original"], inplace=True)

    return df

# ---------- CONECTAR A SHEETS ----------
def conectar():

    creds_json = os.environ.get("GOOGLE_DRIVE_JSON")

    if not creds_json:
        raise Exception("❌ Falta el secret GOOGLE_DRIVE_JSON en GitHub")

    creds = Credentials.from_service_account_info(
        json.loads(creds_json),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    client = gspread.authorize(creds)

    # abrir el sheet correcto
    sh = client.open_by_key(SPREADSHEET_ID)

    return sh.sheet1

# ---------- GUARDAR ----------
def guardar(df):

    ws = conectar()

    columnas = ["medio","titulo_original","titulo_es","link","fecha"]

    # asegurar columnas
    for c in columnas:
        if c not in df.columns:
            df[c] = ""

    # limpieza total
    df = df[columnas].fillna("").astype(str)

    # convertir a lista segura
    data = [columnas]
    for _, row in df.iterrows():
        data.append([str(x) if x is not None else "" for x in row])

    # escribir en hoja
    ws.update(values=data, range_name="A1")

    print("✅ Datos escritos en Google Sheets")

# ---------- MAIN ----------
def main():

    print("🌐 Ejecutando monitoreo…")

    df = recolectar()

    if df.empty:
        print("⚠️ No hay noticias relevantes")
        return

    guardar(df)

    print(f"✅ {len(df)} noticias enviadas al Sheet")

if __name__ == "__main__":
    main()
