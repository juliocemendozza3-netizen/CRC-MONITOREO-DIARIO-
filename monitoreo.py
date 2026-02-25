import feedparser
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
import os, json, gspread
from google.oauth2.service_account import Credentials
from deep_translator import GoogleTranslator

# -------- CONFIG --------
SHEET_ID="1KhVwAHYcwSU6h4U0GTFfFmODVy7ZgV21Q1Ahjo7aoqw"

# -------- FUENTES REGULADORES --------
FUENTES={
    "CRC":"https://news.google.com/rss/search?q=CRC+Colombia+regulación+telecomunicaciones&hl=es&gl=CO&ceid=CO:es",
    "ITU":"https://news.google.com/rss/search?q=ITU+children+digital+safety&hl=en&gl=US&ceid=US:en",
    "OECD":"https://news.google.com/rss/search?q=OECD+children+online+safety+policy&hl=en&gl=US&ceid=US:en",
    "UNICEF":"https://news.google.com/rss/search?q=UNICEF+internet+children+policy&hl=en&gl=US&ceid=US:en",
    "UNESCO":"https://news.google.com/rss/search?q=UNESCO+media+literacy+children+digital&hl=en&gl=US&ceid=US:en",
    "Ofcom":"https://news.google.com/rss/search?q=Ofcom+online+safety+children&hl=en-GB&gl=GB&ceid=GB:en",
    "FCC":"https://news.google.com/rss/search?q=FCC+children+internet+policy&hl=en-US&gl=US&ceid=US:en",
    "FTC":"https://news.google.com/rss/search?q=FTC+children+privacy+online&hl=en-US&gl=US&ceid=US:en",
    "Australia eSafety":"https://news.google.com/rss/search?q=eSafety+Commissioner+children&hl=en-AU&gl=AU&ceid=AU:en",
    "Korea KCC":"https://news.google.com/rss/search?q=Korea+Communications+Commission+children&hl=en&gl=KR&ceid=KR:en",
    "China CAC":"https://news.google.com/rss/search?q=China+internet+regulation+children&hl=en&gl=CN&ceid=CN:en",
    "Regulatel":"https://news.google.com/rss/search?q=Regulatel+telecomunicaciones+niños&hl=es&gl=CO&ceid=CO:es",
    "PRAI":"https://news.google.com/rss/search?q=PRAI+programa+regional+audiovisual+infantil&hl=es&gl=CO&ceid=CO:es"
}

CLAVES=[
    "children","child","kids","minor","youth","teen",
    "privacy","data protection","platform regulation",
    "online safety","digital safety","content moderation",
    "niños","infancia","menores","protección digital",
    "plataformas","regulación","internet","televisión"
]

# -------- FUNCIONES TEXTO --------
def limpiar_titulo(t):
    t=str(t).replace("\n"," ").strip()
    if " - " in t:
        t=t.rsplit(" - ",1)[0]   # quita fuente del final
    return t

def traducir(t):
    try:
        return GoogleTranslator(source="auto",target="es").translate(t)
    except:
        return t

def es_relevante(t):
    return any(p in str(t).lower() for p in CLAVES)

def es_reciente(entry):
    if not hasattr(entry,"published_parsed"):
        return True
    fecha=datetime(*entry.published_parsed[:6],tzinfo=ZoneInfo("UTC"))
    return fecha>=datetime.now(ZoneInfo("UTC"))-timedelta(days=7)

def link_funciona(url):
    try:
        r=requests.head(url,timeout=6,allow_redirects=True)
        return r.status_code<400
    except:
        return False

def detectar_pais(link):
    link=link.lower()
    if ".co" in link: return "Colombia"
    if ".uk" in link: return "Reino Unido"
    if ".au" in link: return "Australia"
    if ".kr" in link: return "Corea"
    if ".cn" in link: return "China"
    if ".eu" in link: return "Europa"
    return "Global"

# -------- RECOLECTAR --------
def recolectar():
    datos=[]

    for regulador,url in FUENTES.items():
        feed=feedparser.parse(url)

        for e in feed.entries:

            if not es_reciente(e):
                continue

            titulo=limpiar_titulo(e.title)

            if not es_relevante(titulo):
                continue

            if not link_funciona(e.link):
                continue

            datos.append({
                "regulador":regulador,
                "pais":detectar_pais(e.link),
                "titulo":titulo,
                "titulo_es":traducir(titulo),
                "link":e.link,
                "fecha":datetime.now(
                    ZoneInfo("America/Bogota")
                ).strftime("%Y-%m-%d %H:%M")
            })

    df=pd.DataFrame(datos)
    if not df.empty:
        df.drop_duplicates(subset=["titulo"],inplace=True)

    return df

# -------- CONECTAR SHEETS --------
def conectar():
    creds_json=os.environ.get("GOOGLE_DRIVE_JSON")
    creds=Credentials.from_service_account_info(
        json.loads(creds_json),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client=gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

# -------- GUARDAR --------
def guardar(df):

    ws=conectar()

    columnas=["regulador","pais","titulo","titulo_es","link","fecha"]
    df=df[columnas].fillna("").astype(str)

    data=[columnas]+df.values.tolist()

    ws.clear()
    ws.update(range_name="A1",values=data)

# -------- MAIN --------
def main():

    df=recolectar()

    if df.empty:
        print("⚠️ No hay noticias recientes válidas")
        return

    guardar(df)
    print(f"✅ {len(df)} noticias válidas guardadas")

if __name__=="__main__":
    main()
