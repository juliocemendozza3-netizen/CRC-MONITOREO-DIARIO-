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


# ---------- FILTRO CRC ESTRICTO ----------
CLAVES_MENORES=["children","child","minor","teen","youth","niños","infancia","menores","adolescentes"]
CLAVES_RED_SOCIAL=["social media","platform","tiktok","instagram","facebook","youtube","snapchat","redes sociales","plataformas"]

def es_tema_crc(t):
    t=t.lower()
    return any(k in t for k in CLAVES_MENORES) and any(k in t for k in CLAVES_RED_SOCIAL)


# ---------- FILTRO EVENTOS ----------
EVENTOS=["forum","summit","conference","webinar","seminar","workshop","meeting","foro","cumbre","conferencia","seminario","taller","evento"]
def es_evento(t):
    return any(e in t.lower() for e in EVENTOS)


# ---------- CLASIFICACIÓN ----------
TEMAS={
    "Privacidad":["privacy","data protection","consent"],
    "Plataformas":["platform","social media","moderation"],
    "Alfabetización":["literacy","education","training"],
    "Seguridad":["online safety","risk","harm"],
    "IA":["ai","artificial intelligence","algorithm","deepfake"]
}

ACCIONES={
    "Regulación":["law","regulation","rule","bill"],
    "Política":["policy","strategy","plan"],
    "Guía":["guide","guideline","recommendation"],
    "Sanción":["fine","penalty","investigation"],
    "Programa":["campaign","initiative"]
}

def detectar(dic,t):
    t=t.lower()
    for k,v in dic.items():
        if any(p in t for p in v):
            return k
    return "Otros"


# ---------- UTILIDADES ----------
def traducir(t):
    try: return GoogleTranslator(source="auto",target="es").translate(t)
    except: return t

def limpiar_link(url):
    try:
        if "news.google.com" in url:
            r=requests.get(url,timeout=6,allow_redirects=True,headers={"User-Agent":"Mozilla/5.0"})
            return r.url
        return url
    except: return url

def link_valido(url):
    try:
        r=requests.head(url,timeout=5,allow_redirects=True,headers={"User-Agent":"Mozilla/5.0"})
        return r.status_code<400
    except: return False

def es_reciente(entry):
    if hasattr(entry,"published_parsed") and entry.published_parsed:
        fecha=datetime(*entry.published_parsed[:6])
        return fecha>=datetime.now()-timedelta(days=365)
    return False

def fecha_noticia(entry):
    if hasattr(entry,"published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
    return ""


# ---------- RECOLECTAR ----------
def recolectar():
    datos=[]
    for reg,url in FUENTES.items():
        feed=feedparser.parse(url)
        for e in feed.entries:

            if not es_reciente(e): continue

            titulo=e.title.strip()

            if es_evento(titulo): continue
            if not es_tema_crc(titulo): continue

            link=limpiar_link(e.link)
            if not link_valido(link): continue

            meta=META.get(reg,{"pais":"Internacional","region":"Global","tipo":"Otro"})

            datos.append({
                "regulador":reg,
                "pais":meta["pais"],
                "region":meta["region"],
                "tipo_actor":meta["tipo"],
                "tema":detectar(TEMAS,titulo),
                "intervencion":detectar(ACCIONES,titulo),
                "titulo_original":titulo,
                "titulo_es":traducir(titulo),
                "link":link,
                "fecha_noticia":fecha_noticia(e),
                "fecha_busqueda":datetime.now(ZoneInfo("America/Bogota")).strftime("%Y-%m-%d")
            })

    df=pd.DataFrame(datos)
    if not df.empty:
        df.drop_duplicates(subset=["titulo_original"],inplace=True)
        df["intensidad"]=df.groupby("tema")["tema"].transform("count")
    return df


# ---------- SHEETS ----------
def conectar():
    creds_json=os.environ.get("GOOGLE_DRIVE_JSON")
    creds=Credentials.from_service_account_info(json.loads(creds_json),
        scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client=gspread.authorize(creds)
    return client.open_by_key("1KhVwAHYcwSU6h4U0GTFfFmODVy7ZgV21Q1Ahjo7aoqw").sheet1


def guardar(df):
    ws=conectar()
    columnas=[
        "regulador","pais","region","tipo_actor",
        "tema","intervencion","intensidad",
        "titulo_original","titulo_es","link",
        "fecha_noticia","fecha_busqueda"
    ]
    df=df[columnas].fillna("").astype(str)
    ws.update(range_name="A1",values=[columnas]+df.values.tolist())
    print("✅ Monitoreo CRC final actualizado")


# ---------- MAIN ----------
def main():
    df=recolectar()
    if df.empty:
        print("⚠️ No hay noticias relevantes")
        return
    guardar(df)
    print(f"✅ {len(df)} noticias procesadas")

if __name__=="__main__":
    main()
