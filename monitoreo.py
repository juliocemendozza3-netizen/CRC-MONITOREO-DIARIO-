import feedparser
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import json
import gspread
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

def relevante(texto):
    return any(p in str(texto).lower() for p in CLAVES)

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

# ---------- LIMPIEZA ----------
def limpiar_df(df):
    df=df.replace([float("inf"),float("-inf")],"")
    df=df.fillna("")
    for c in df.columns:
        df[c]=df[c].astype(str)
    return df

# ---------- GUARDAR ----------
def guardar(df):

    creds_json=os.environ.get("GOOGLE_DRIVE_JSON")
    if not creds_json:
        print("❌ NO existe GOOGLE_DRIVE_JSON")
        return

    creds=Credentials.from_service_account_info(
        json.loads(creds_json),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

    client=gspread.authorize(creds)

    # 🔴 AQUÍ ESTÁ LA CLAVE: abrir SIEMPRE el Sheet
    sh=client.open_by_key("1Lq0tTUSnsBAoJ7OClP8DsdvPcNuCI3Fdviup-gBAteY")

    # usar hoja principal (siempre existe)
    ws=sh.sheet1

    columnas=["medio","titulo_original","titulo_es","link","fecha"]

    for c in columnas:
        if c not in df.columns:
            df[c]=""

    df=df[columnas]
    df=limpiar_df(df)

    existentes=ws.get_all_values()

    if existentes:
        old=pd.DataFrame(existentes[1:],columns=existentes[0])
        old=limpiar_df(old)
        df=pd.concat([old,df],ignore_index=True)

    df.drop_duplicates(subset=["titulo_original"],inplace=True)

    data=[columnas]+df.values.tolist()

    ws.update("A1",data)

    print("✅ ESCRITO EN GOOGLE SHEETS")

# ---------- MAIN ----------
def main():

    df=recolectar()

    if df.empty:
        print("⚠️ No hay noticias relevantes")
        return

    guardar(df)

    print(f"✅ {len(df)} noticias enviadas a Sheets")

if __name__=="__main__":
    main()
