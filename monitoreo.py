import feedparser
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os, json, gspread, requests
from google.oauth2.service_account import Credentials
from deep_translator import GoogleTranslator


# ---------- METADATOS REGULADORES ----------
META={
    "CRC":{"pais":"Colombia","region":"Latinoamérica","tipo":"Regulador"},
    "Ofcom":{"pais":"Reino Unido","region":"Europa","tipo":"Regulador"},
    "FCC":{"pais":"Estados Unidos","region":"Norteamérica","tipo":"Regulador"},
    "FTC":{"pais":"Estados Unidos","region":"Norteamérica","tipo":"Regulador"},
    "eSafety Commissioner":{"pais":"Australia","region":"Oceanía","tipo":"Regulador"},
    "KCC":{"pais":"Corea del Sur","region":"Asia","tipo":"Regulador"},
    "CAC China":{"pais":"China","region":"Asia","tipo":"Regulador"},
    "ITU":{"pais":"Internacional","region":"Global","tipo":"Organismo internacional"},
    "OECD":{"pais":"Internacional","region":"Global","tipo":"Organismo internacional"},
    "UNICEF":{"pais":"Internacional","region":"Global","tipo":"Organismo internacional"},
    "UNESCO":{"pais":"Internacional","region":"Global","tipo":"Organismo internacional"},
    "Regulatel":{"pais":"Latinoamérica","region":"Latinoamérica","tipo":"Red regulatoria"},
    "PRAI":{"pais":"Latinoamérica","region":"Latinoamérica","tipo":"Programa regional"}
}


# ---------- FUENTES ----------
FUENTES={
    "CRC":"https://news.google.com/rss/search?q=CRC+Colombia+regulación+telecomunicaciones&hl=es&gl=CO&ceid=CO:es",
    "ITU":"https://news.google.com/rss/search?q=ITU+children+digital+safety&hl=en&gl=US&ceid=US:en",
    "OECD":"https://news.google.com/rss/search?q=OECD+children+online+safety+policy&hl=en&gl=US&ceid=US:en",
    "UNICEF":"https://news.google.com/rss/search?q=UNICEF+internet+children+policy&hl=en&gl=US&ceid=US:en",
    "UNESCO":"https://news.google.com/rss/search?q=UNESCO+media+literacy+children+digital&hl=en&gl=US&ceid=US:en",
    "Ofcom":"https://news.google.com/rss/search?q=Ofcom+online+safety+children&hl=en-GB&gl=GB&ceid=GB:en",
    "FCC":"https://news.google.com/rss/search?q=FCC+children+internet+policy&hl=en-US&gl=US&ceid=US:en",
    "FTC":"https://news.google.com/rss/search?q=FTC+children+privacy+online&hl=en-US&gl=US&ceid=US:en",
    "eSafety Commissioner":"https://news.google.com/rss/search?q=Australia+eSafety+Commissioner+children&hl=en-AU&gl=AU&ceid=AU:en",
    "KCC":"https://news.google.com/rss/search?q=Korea+Communications+Commission+children+internet&hl=en&gl=KR&ceid=KR:en",
    "CAC China":"https://news.google.com/rss/search?q=China+internet+regulation+children+gaming&hl=en&gl=CN&ceid=CN:en",
    "Regulatel":"https://news.google.com/rss/search?q=Regulatel+telecomunicaciones&hl=es&gl=CO&ceid=CO:es",
    "PRAI":"https://news.google.com/rss/search?q=PRAI+infancia+televisión+educativa&hl=es&gl=CO&ceid=CO:es"
}


# ---------- PALABRAS CLAVE ----------
CLAVES=[
    "children","child","kids","minor","youth","teen",
    "privacy","data protection","platform regulation",
    "online safety","digital safety","content moderation",
    "ai regulation","screen time","parental control",
    "niños","infancia","menores","protección digital",
    "plataformas","regulación","internet","televisión"
]

TIPO_POLITICA={
    "ley":"Legislación",
    "law":"Legislación",
    "regulation":"Regulación",
    "policy":"Política pública",
    "agreement":"Acuerdo",
    "guideline":"Guía",
    "framework":"Marco regulatorio"
}


# ---------- UTILIDADES ----------
def limpiar(t):
    t=str(t).replace("\n"," ").strip()
    if " - " in t:
        t=t.rsplit(" - ",1)[0]
    return t

def relevante(t):
    return any(p in str(t).lower() for p in CLAVES)

def traducir(t):
    try:
        return GoogleTranslator(source="auto",target="es").translate(t)
    except:
        return t

def detectar_tipo(texto):
    texto=texto.lower()
    for k,v in TIPO_POLITICA.items():
        if k in texto:
            return v
    return "General"

def es_reciente(entry):
    if hasattr(entry,"published_parsed") and entry.published_parsed:
        fecha=datetime(*entry.published_parsed[:6])
        return fecha>=datetime.now()-timedelta(days=7)
    return False

def link_valido(url):
    try:
        r=requests.get(url,timeout=6,headers={"User-Agent":"Mozilla/5.0"})
        return r.status_code==200
    except:
        return False


# ---------- RECOLECTAR ----------
def recolectar():

    datos=[]

    for reg,url in FUENTES.items():

        feed=feedparser.parse(url)

        for e in feed.entries:

            if not es_reciente(e):
                continue

            titulo=limpiar(e.title)

            if not relevante(titulo):
                continue

            if not link_valido(e.link):
                continue

            meta=META.get(reg,{"pais":"Internacional","region":"Global","tipo":"Otro"})

            datos.append({
                "regulador":reg,
                "pais":meta["pais"],
                "region":meta["region"],
                "tipo_actor":meta["tipo"],
                "tipo_politica":detectar_tipo(titulo),
                "titulo_original":titulo,
                "titulo_es":traducir(titulo),
                "link":e.link,
                "fecha":datetime.now(ZoneInfo("America/Bogota")).strftime("%Y-%m-%d %H:%M")
            })

    df=pd.DataFrame(datos)

    if not df.empty:
        df.drop_duplicates(subset=["titulo_original"],inplace=True)

    return df


# ---------- CONECTAR SHEETS ----------
def conectar():

    creds_json=os.environ.get("GOOGLE_DRIVE_JSON")

    creds=Credentials.from_service_account_info(
        json.loads(creds_json),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    client=gspread.authorize(creds)

    sh=client.open_by_key("1KhVwAHYcwSU6h4U0GTFfFmODVy7ZgV21Q1Ahjo7aoqw")

    return sh.sheet1


# ---------- GUARDAR ----------
def guardar(df):

    ws=conectar()

    columnas=[
        "regulador","pais","region","tipo_actor",
        "tipo_politica","titulo_original","titulo_es","link","fecha"
    ]

    df=df[columnas].fillna("").astype(str)

    ws.update(range_name="A1",values=[columnas]+df.values.tolist())

    print("✅ Monitoreo CRC actualizado")


# ---------- MAIN ----------
def main():

    df=recolectar()

    if df.empty:
        print("⚠️ No hay noticias recientes relevantes")
        return

    guardar(df)

    print(f"✅ {len(df)} noticias procesadas")


if __name__=="__main__":
    main()
