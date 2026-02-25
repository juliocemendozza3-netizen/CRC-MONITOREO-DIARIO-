import feedparser
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os, json, gspread
from google.oauth2.service_account import Credentials
from deep_translator import GoogleTranslator
from dateutil import parser as dateparser


# ---------- FUENTES ----------
FUENTES = {

    "CRC Colombia":
        "https://news.google.com/rss/search?q=CRC+Colombia+regulación+digital+menores&hl=es&gl=CO&ceid=CO:es",

    "UIT":
        "https://news.google.com/rss/search?q=ITU+children+digital+safety&hl=en&gl=US&ceid=US:en",

    "OCDE":
        "https://news.google.com/rss/search?q=OECD+children+online+safety+policy&hl=en&gl=US&ceid=US:en",

    "UNICEF":
        "https://news.google.com/rss/search?q=UNICEF+internet+children+policy&hl=en&gl=US&ceid=US:en",

    "UNESCO":
        "https://news.google.com/rss/search?q=UNESCO+media+literacy+children+digital&hl=en&gl=US&ceid=US:en",

    "Ofcom":
        "https://news.google.com/rss/search?q=Ofcom+online+safety+children&hl=en-GB&gl=GB&ceid=GB:en",

    "FCC":
        "https://news.google.com/rss/search?q=FCC+children+internet+policy&hl=en-US&gl=US&ceid=US:en",

    "FTC":
        "https://news.google.com/rss/search?q=FTC+children+privacy+online&hl=en-US&gl=US&ceid=US:en",

    "eSafety Commissioner":
        "https://news.google.com/rss/search?q=Australia+eSafety+Commissioner+children&hl=en-AU&gl=AU&ceid=AU:en",

    "KCC":
        "https://news.google.com/rss/search?q=Korea+Communications+Commission+children+internet&hl=en&gl=KR&ceid=KR:en",

    "CAC China":
        "https://news.google.com/rss/search?q=China+internet+regulation+children+gaming&hl=en&gl=CN&ceid=CN:en",

    "Regulatel":
        "https://news.google.com/rss/search?q=Regulatel+telecom+children&hl=es&gl=CO&ceid=CO:es",

    "PRAI":
        "https://news.google.com/rss/search?q=programa+regional+audiovisual+infantil+PRAI&hl=es&gl=CO&ceid=CO:es"
}


# ---------- MAPA REGULADOR → PAÍS ----------
PAISES = {
    "CRC Colombia":"Colombia",
    "Ofcom":"Reino Unido",
    "FCC":"Estados Unidos",
    "FTC":"Estados Unidos",
    "eSafety Commissioner":"Australia",
    "KCC":"Corea del Sur",
    "CAC China":"China",
    "Regulatel":"Latinoamérica",
    "PRAI":"Latinoamérica",
    "UIT":"Internacional",
    "OCDE":"Internacional",
    "UNICEF":"Internacional",
    "UNESCO":"Internacional"
}


CLAVES = [
    "children","child","kids","minor","youth","teen",
    "privacy","data protection","platform regulation",
    "online safety","digital safety","content moderation",
    "ai regulation","screen time","parental control",
    "niños","infancia","menores","protección digital",
    "plataformas","regulación","internet","televisión"
]


# ---------- TEXTO ----------
def limpiar(texto):
    return " ".join(str(texto).replace("\n"," ").split())

def traducir(texto):
    try:
        return GoogleTranslator(source="auto", target="es").translate(texto)
    except:
        return texto

def relevante(texto):
    return any(p in str(texto).lower() for p in CLAVES)


# ---------- FILTRO SEMANA ----------
def es_reciente(entry):
    fecha_raw = entry.get("published") or entry.get("updated")
    if not fecha_raw:
        return False
    try:
        fecha = dateparser.parse(fecha_raw)
        ahora = datetime.now(ZoneInfo("America/Bogota"))
        return fecha >= (ahora - timedelta(days=7))
    except:
        return False


# ---------- LIMPIAR TITULO ----------
def limpiar_titulo_fuente(titulo, regulador):

    titulo = limpiar(titulo)
    separadores = [" - "," | "," — "," – "]

    for sep in separadores:
        if sep in titulo:
            partes = titulo.rsplit(sep,1)
            posible_fuente = partes[1].strip()
            if len(posible_fuente.split()) <= 4:
                return partes[0].strip(), posible_fuente

    return titulo, regulador


# ---------- RECOLECTAR ----------
def recolectar():

    datos = []

    for regulador, url in FUENTES.items():

        feed = feedparser.parse(url)

        for e in feed.entries:

            if not es_reciente(e):
                continue

            titulo, fuente = limpiar_titulo_fuente(e.title, regulador)

            if not relevante(titulo):
                continue

            datos.append({
                "pais": PAISES.get(regulador,"Internacional"),
                "regulador": regulador,
                "fuente": fuente,
                "titulo_original": titulo,
                "titulo_es": traducir(titulo),
                "link": e.link,
                "fecha_captura": datetime.now(
                    ZoneInfo("America/Bogota")
                ).strftime("%Y-%m-%d %H:%M")
            })

    df = pd.DataFrame(datos)

    if not df.empty:
        df.drop_duplicates(subset=["titulo_original"], inplace=True)

    return df


# ---------- CONECTAR SHEETS ----------
def conectar():

    creds_json = os.environ.get("GOOGLE_DRIVE_JSON")
    if not creds_json:
        raise Exception("Falta GOOGLE_DRIVE_JSON")

    creds = Credentials.from_service_account_info(
        json.loads(creds_json),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    client = gspread.authorize(creds)
    sh = client.open_by_key("1KhVwAHYcwSU6h4U0GTFfFmODVy7ZgV21Q1Ahjo7aoqw")

    return sh.sheet1


# ---------- GUARDAR ----------
def guardar(df):

    ws = conectar()

    columnas = [
        "pais","regulador","fuente",
        "titulo_original","titulo_es",
        "link","fecha_captura"
    ]

    df = df[columnas].fillna("").astype(str)

    data = [columnas] + df.values.tolist()

    ws.clear()
    ws.update(range_name="A1", values=data)

    print("✅ Sheet actualizado con país y noticias recientes")


# ---------- MAIN ----------
def main():

    df = recolectar()

    if df.empty:
        print("⚠️ No hay noticias recientes")
        return

    guardar(df)

    print(f"✅ {len(df)} noticias enviadas")


if __name__ == "__main__":
    main()
