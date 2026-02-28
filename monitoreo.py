import feedparser
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os, json, gspread, requests, re
from google.oauth2.service_account import Credentials
from deep_translator import GoogleTranslator


# ---------- METADATOS ----------
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


# ---------- CLASIFICADORES ----------
TEMAS={
    "IA":["ai","artificial intelligence","algoritmo","deepfake"],
    "Privacidad":["privacy","data protection","consent"],
    "Plataformas":["platform","social media","moderation"],
    "Alfabetizacion":["literacy","education","training"],
    "Seguridad":["online safety","risk","harm"]
}

ACCIONES={
    "Regulación":["law","regulation","rule","bill"],
    "Política":["policy","strategy","plan"],
    "Guía":["guide","guideline","recommendation"],
    "Sanción":["fine","penalty","investigation"],
    "Programa":["campaign","initiative"]
}


# ---------- UTILIDADES ----------
def limpiar_texto(t):
    t=str(t)
    t=t.replace("\n"," ").strip()
    t=re.sub(r'\b\d+\b', '', t)
    t=" ".join(t.split())
    return t


# 🔴 CAMBIO APLICADO AQUÍ
def traducir(t):
    try:
        trad=GoogleTranslator(source="auto",target="es").translate(t)

        # Si la traducción es igual al original,
        # asumimos que ya está en español y lo repetimos
        if trad.lower()==t.lower():
            return t

        return trad
    except:
        return t


def detectar_tema(t):
    t=t.lower()
    for tema,pal in TEMAS.items():
        if any(p in t for p in pal):
            return tema
    return "Otros"


def detectar_accion(t):
    t=t.lower()
    for a,pal in ACCIONES.items():
        if any(p in t for p in pal):
            return a
    return "Informativo"


def obtener_fecha(entry):
    if hasattr(entry,"published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
    return ""


def link_valido(url):
    try:
        r=requests.head(url,timeout=5,allow_redirects=True,
                        headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code<400:
            return True
        r=requests.get(url,timeout=6,allow_redirects=True,
                       headers={"User-Agent":"Mozilla/5.0"})
        return r.status_code<400
    except:
        return False


# ---------- RECOLECTAR ----------
def recolectar():

    datos=[]

    for reg,url in FUENTES.items():

        feed=feedparser.parse(url)

        for e in feed.entries:

            titulo=limpiar_texto(e.title)

            if not link_valido(e.link):
                continue

            meta=META.get(reg,{"pais":"Internacional","region":"Global","tipo":"Otro"})

            datos.append({
                "regulador":reg,
                "pais":meta["pais"],
                "region":meta["region"],
                "tipo_actor":meta["tipo"],
                "tema_global":detectar_tema(titulo),
                "accion_regulatoria":detectar_accion(titulo),
                "contexto_crc":"Alfabetización" if "literacy" in titulo.lower() else "Regulación",
                "titulo_original":titulo,
                "titulo_es":traducir(titulo),
                "link":str(e.link).strip(),
                "fecha_noticia":obtener_fecha(e),
                "fecha_busqueda":datetime.now(ZoneInfo("America/Bogota")).strftime("%Y-%m-%d")
            })

    df=pd.DataFrame(datos)

    if not df.empty:
        df.drop_duplicates(subset=["titulo_original"],inplace=True)

    return df


# ---------- SHEETS ----------
def conectar():
    creds_json=os.environ.get("GOOGLE_DRIVE_JSON")
    creds=Credentials.from_service_account_info(json.loads(creds_json),
        scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client=gspread.authorize(creds)
    sh=client.open_by_key("1KhVwAHYcwSU6h4U0GTFfFmODVy7ZgV21Q1Ahjo7aoqw")
    return sh.sheet1


def guardar(df):

    ws=conectar()

    columnas=[
        "regulador","pais","region","tipo_actor",
        "tema_global","accion_regulatoria","contexto_crc",
        "titulo_original","titulo_es","link",
        "fecha_noticia","fecha_busqueda"
    ]

    df=df[columnas].fillna("").astype(str)

    for col in ["titulo_original","titulo_es"]:
        df[col]=df[col].apply(limpiar_texto)

    ws.update(range_name="A1",values=[columnas]+df.values.tolist())

    print("✅ Sheet limpio, ordenado y funcional")


# ---------- MAIN ----------
def main():

    df=recolectar()

    if df.empty:
        print("⚠️ No hay noticias")
        return

    guardar(df)

    print(f"✅ {len(df)} noticias procesadas")


if __name__=="__main__":
    main()
