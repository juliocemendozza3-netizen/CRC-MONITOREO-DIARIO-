import feedparser
import pandas as pd
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from deep_translator import GoogleTranslator

TOKEN = "TU_TOKEN"
CHAT_ID = "TU_CHAT"

def enviar_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# -------- FUENTES --------
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

CLAVES = [
    "children","child","kids","minor","youth","teen",
    "privacy","data protection","platform regulation",
    "online safety","digital safety","content moderation",
    "ai regulation","screen time","parental control",
    "niños","infancia","menores","protección digital",
    "plataformas","regulación","internet","televisión"
]

def limpiar(t):
    return " ".join(str(t).replace("\n"," ").split())

def relevante(texto):
    texto = str(texto).lower()
    return any(p in texto for p in CLAVES)

def traducir(texto):
    try:
        return GoogleTranslator(source="auto", target="es").translate(texto)
    except:
        return texto

# -------- RECOLECTAR --------
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
    df.drop_duplicates(subset=["titulo_original"], inplace=True)
    return df

# -------- LIMPIEZA SEGURA --------
def limpiar_dataframe(df):

    df=df.replace([float("inf"),float("-inf")],None)
    df=df.where(pd.notnull(df),None)
    df=df.astype(object).fillna("").astype(str)

    for col in df.columns:
        df[col]=df[col].apply(
            lambda x: x.encode("utf-8","ignore").decode("utf-8") if isinstance(x,str) else x
        )

    return df

# -------- GUARDAR --------
def guardar(df):

    creds_json=os.environ.get("GOOGLE_DRIVE_JSON")
    if not creds_json:
        enviar_telegram("❌ Falta GOOGLE_DRIVE_JSON")
        return

    creds=Credentials.from_service_account_info(
        json.loads(creds_json),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

    client=gspread.authorize(creds)
    sh=client.open_by_key("1Lq0tTUSnsBAoJ7OClP8DsdvPcNuCI3Fdviup-gBAteY")

    try:
        ws=sh.worksheet("Tecnologia")
    except:
        ws=sh.sheet1
        enviar_telegram("⚠️ Usando hoja principal")

    columnas=["medio","titulo_original","titulo_es","link","fecha"]

    for c in columnas:
        if c not in df.columns:
            df[c]=""

    df=df[columnas]
    df=limpiar_dataframe(df)

    existentes=ws.get_all_values()

    if existentes:
        old=pd.DataFrame(existentes[1:],columns=existentes[0])
        old=limpiar_dataframe(old)
        df=pd.concat([old,df],ignore_index=True)

    df.drop_duplicates(subset=["titulo_original"], inplace=True)

    ws.update(values=[columnas]+df.values.tolist(), range_name="A1")

# -------- MAIN --------
def main():

    enviar_telegram("🌐 Monitoreo global protección infantil digital")

    df=recolectar()

    if df.empty:
        enviar_telegram("⚠️ No se detectaron noticias relevantes")
        return

    guardar(df)

    enviar_telegram(f"✅ {len(df)} noticias registradas")

if __name__=="__main__":
    main()
