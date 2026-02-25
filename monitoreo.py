import feedparser
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import os, json, gspread
from google.oauth2.service_account import Credentials
from deep_translator import GoogleTranslator

# ---------- FUENTES ----------
FUENTES={
    "Google Tech Global":"https://news.google.com/rss/search?q=technology+regulation+children+privacy+platforms&hl=en-US&gl=US&ceid=US:en",
    "Google Policy Europe":"https://news.google.com/rss/search?q=digital+regulation+EU+children+internet+law&hl=en-GB&gl=GB&ceid=GB:en",
    "Google Latam Tech":"https://news.google.com/rss/search?q=regulacion+digital+niños+internet+plataformas&hl=es-419&gl=CO&ceid=CO:es-419",
    "TechCrunch":"https://techcrunch.com/tag/policy/feed/",
    "The Verge Policy":"https://www.theverge.com/rss/policy/index.xml"
}

CLAVES=[
    "children","child","kids","minor","youth","teen",
    "privacy","data protection","platform regulation",
    "online safety","digital safety","content moderation",
    "ai regulation","screen time","parental control",
    "niños","infancia","menores","protección digital",
    "plataformas","regulación","internet","televisión"
]

# ---------- TEXTO ----------
def limpiar(t):
    return " ".join(str(t).replace("\n"," ").split())

def relevante(t):
    return any(p in str(t).lower() for p in CLAVES)

def traducir(t):
    try:
        return GoogleTranslator(source="auto",target="es").translate(t)
    except:
        return t

# ---------- RECOLECTAR ----------
def recolectar():
    datos=[]
    for medio,url in FUENTES.items():
        feed=feedparser.parse(url)
        for e in feed.entries:
            titulo=limpiar(e.title)
            if not relevante(titulo):
                continue
            datos.append({
                "medio":medio,
                "titulo_original":titulo,
                "titulo_es":traducir(titulo),
                "link":e.link,
                "fecha":datetime.now(
                    ZoneInfo("America/Bogota")
                ).strftime("%Y-%m-%d %H:%M")
            })
    df=pd.DataFrame(datos)
    if not df.empty:
        df.drop_duplicates(subset=["titulo_original"],inplace=True)
    return df

# ---------- CONECTAR ----------
def conectar():

    creds_json=os.environ.get("GOOGLE_DRIVE_JSON")
    if not creds_json:
        raise Exception("Falta GOOGLE_DRIVE_JSON en GitHub")

    creds=Credentials.from_service_account_info(
        json.loads(creds_json),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    client=gspread.authorize(creds)
    sh=client.open_by_key("1Lq0tTUSnsBAoJ7OClP8DsdvPcNuCI3Fdviup-gBAteY")

    return sh.sheet1

# ---------- GUARDAR ----------
def guardar(df):

    ws=conectar()

    columnas=["medio","titulo_original","titulo_es","link","fecha"]

    for c in columnas:
        if c not in df.columns:
            df[c]=""

    df=df[columnas].fillna("").astype(str)

    data=[columnas]+df.values.tolist()

    ws.update(range_name="A1", values=data)

    print("✅ Datos escritos en Google Sheets")

# ---------- MAIN ----------
def main():

    df=recolectar()

    if df.empty:
        print("⚠️ No hay noticias relevantes")
        return

    guardar(df)

    print(f"✅ {len(df)} noticias enviadas")

if __name__=="__main__":
    main()
