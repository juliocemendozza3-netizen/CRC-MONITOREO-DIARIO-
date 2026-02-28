import feedparser
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os, json, gspread, requests, re
from google.oauth2.service_account import Credentials
from deep_translator import GoogleTranslator


# ---------- LIMPIEZA TEXTO ----------
def limpiar_texto(t):
    t=str(t)

    # quitar saltos
    t=t.replace("\n"," ").strip()

    # quitar números sueltos
    t=re.sub(r'\b\d+\b', '', t)

    # quitar dobles espacios
    t=" ".join(t.split())

    return t


def traducir(t):
    try:
        trad=GoogleTranslator(source="auto",target="es").translate(t)
        if trad.strip().lower()==t.strip().lower():
            return ""   # evitar duplicado
        return trad
    except:
        return ""


# ---------- VALIDAR LINK ----------
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


# ---------- GUARDAR ORDENADO ----------
def guardar(df):

    ws=conectar()

    columnas=[
        "regulador","pais","region","tipo_actor",
        "tema_global","accion_regulatoria","contexto_crc",
        "titulo_original","titulo_es","link",
        "fecha_noticia","fecha_busqueda"
    ]

    # 🔴 forzar orden correcto
    df=df[columnas].fillna("").astype(str)

    # 🔴 eliminar números sueltos otra vez por seguridad
    for col in ["titulo_original","titulo_es"]:
        df[col]=df[col].apply(limpiar_texto)

    ws.update(range_name="A1",values=[columnas]+df.values.tolist())

    print("✅ Sheet ordenado y limpio correctamente")


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
