import feedparser
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import os, json, gspread
from google.oauth2.service_account import Credentials
from deep_translator import GoogleTranslator


# ---------- FUENTES REGULADORES ----------
FUENTES={
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
    "Regulatel":"https://news.google.com/rss/search?q=Regulatel+Latin+America+telecom+children&hl=es&gl=CO&ceid=CO:es",
    "PRAI":"https://news.google.com/rss/search?q=programa+regional+audiovisual+infantil+PRAI&hl=es&gl=CO&ceid=CO:es"
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

# ---------- LIMPIEZA TEXTO ----------
def limpiar(t):
    return " ".join(str(t).replace("\n"," ").split())

# ---------- LIMPIAR TITULO Y EXTRAER FUENTE ----------
def limpiar_titulo_y_fuente(titulo, regulador):

    titulo=limpiar(titulo)
    separadores=[" - "," | "," — "," – "]

    for sep in separadores:
        if sep in titulo:
            partes=titulo.rsplit(sep,1)
            posible_fuente=partes[1].strip()

            # si parece nombre de medio
            if len(posible_fuente.split())<=4:
                return partes[0].strip(), posible_fuente

    return titulo, regulador

# ---------- FILTRO TEMÁTICO ----------
def relevante(t):
    return any(p in str(t).lower() for p in CLAVES)

# ---------- TRADUCCIÓN ----------
def traducir(t):
    try:
        return GoogleTranslator(source="auto",target="es").translate(t)
    except:
        return t

# ---------- RECOLECTAR ----------
def recolectar():

    datos=[]

    for regulador,url in FUENTES.items():
        feed=feedparser.parse(url)

        for e in feed.entries:

            titulo_limpio, fuente = limpiar_titulo_y_fuente(e.title, regulador)

            if not relevante(titulo_limpio):
                continue

            datos.append({
                "regulador":regulador,
                "fuente":fuente,
                "titulo_original":titulo_limpio,
                "titulo_es":traducir(titulo_limpio),
                "link":str(e.link),
                "fecha":datetime.now(
                    ZoneInfo("America/Bogota")
                ).strftime("%Y-%m-%d %H:%M")
            })

    df=pd.DataFrame(datos)

    if not df.empty:
        df.drop_duplicates(subset=["titulo_original"],inplace=True)

    return df

# ---------- CONECTAR A SHEETS ----------
def conectar():

    creds_json=os.environ.get("GOOGLE_DRIVE_JSON")
    if not creds_json:
        raise Exception("Falta GOOGLE_DRIVE_JSON")

    creds=Credentials.from_service_account_info(
        json.loads(creds_json),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    client=gspread.authorize(creds)

    # TU SHEET REAL
    sh=client.open_by_key("1KhVwAHYcwSU6h4U0GTFfFmODVy7ZgV21Q1Ahjo7aoqw")

    return sh.sheet1

# ---------- GUARDAR ----------
def guardar(df):

    ws=conectar()

    columnas=["regulador","fuente","titulo_original","titulo_es","link","fecha"]

    for c in columnas:
        if c not in df.columns:
            df[c]=""

    df=df[columnas]

    # convertir todo a texto seguro
    df=df.fillna("").astype(str)

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
