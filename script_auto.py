from datetime import datetime, timedelta
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import glob
import os
import smtplib
import pandas as pd

# Servidor SMTP SSL de Google Workspace (port 465)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = os.environ.get("EMAIL_USER")
SENDER_PASSWORD = os.environ.get("EMAIL_PASS")

LOG_FILE = "enviats_log.csv"
DIES_RECORDATORI = 7
DATA_AVUI = datetime.today().date()

# Carregar o crear el log
if os.path.exists(LOG_FILE):
  df_log = pd.read_csv(LOG_FILE)
else:
  df_log = pd.DataFrame(
      columns=[
          "ID_UNICI",
          "TIPUS_CORREU",
          "CODI_ACTIVITAT",
          "DESTINATARI",
          "DATA_ENVIAMENT",
      ]
  )


def netejar_dataframe(df):
  df.columns = df.columns.str.strip().str.upper()
  return df


def carregar_csv(filepath):
  for sep in [",", ";", "\t"]:
    try:
      df = pd.read_csv(filepath, encoding="latin1", sep=sep)
      if len(df.columns) > 1:
        return netejar_dataframe(df)
    except Exception:
      continue
  return None


def parse_data(data_str):
  if pd.isna(data_str):
    return None
  data_str = str(data_str).strip()
  for fmt in ["%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
    try:
      return datetime.strptime(data_str, fmt).date()
    except ValueError:
      pass
  return None


def enviar_correus_smtp(llista_correus):
  if not llista_correus:
    print("ℹ️ No hi ha correus pendents per enviar avui.")
    return

  if not SENDER_EMAIL or not SENDER_PASSWORD:
    print("❌ Error: Credencials EMAIL_USER o EMAIL_PASS absents.")
    return

  enviats_exit = []
  try:
    # Connexió directa per SSL (port 465)
    server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
    server.login(SENDER_EMAIL, SENDER_PASSWORD)

    for item in llista_correus:
      msg = MIMEMultipart()
      msg["From"] = SENDER_EMAIL
      msg["To"] = item["Destinatari"]
      msg["Subject"] = item["Assumpte"]
      msg.attach(MIMEText(item["Cos"], "plain"))

      server.send_message(msg)
      print(f"✅ Enviat correu a {item['Destinatari']} - {item['Assumpte']}")

      enviats_exit.append({
          "ID_UNICI": item["ID_UNICI"],
          "TIPUS_CORREU": item["ID_UNICI"].split("_")[0],
          "CODI_ACTIVITAT": str(item["Activitat"]).split()[0],
          "DESTINATARI": item["Destinatari"],
          "DATA_ENVIAMENT": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      })

    server.quit()

    global df_log
    df_nous = pd.DataFrame(enviats_exit)
    df_log = pd.concat([df_log, df_nous], ignore_index=True)
    df_log.to_csv(LOG_FILE, index=False)
    print(f"🎉 Procés finalitzat: {len(enviats_exit)} correus enviats.")

  except Exception as e:
    print(f"❌ Error durant l'enviament: {e}")


# Cercar els CSVs
fitxers_csv = [f for f in glob.glob("*.csv") if f != LOG_FILE]
df_f, df_m = None, None

for f in fitxers_csv:
  temp_df = carregar_csv(f)
  if temp_df is not None:
    if "DATA_INICI" in temp_df.columns or "DATA_FINAL" in temp_df.columns:
      df_f = temp_df
    elif "IND_ASSIGNACIO" in temp_df.columns or "NOM_MAIL" in temp_df.columns:
      df_m = temp_df

if df_f is not None:
  df_f["DATA_INICI_DT"] = df_f["DATA_INICI"].apply(parse_data)
  df_f["DATA_FINAL_DT"] = df_f["DATA_FINAL"].apply(parse_data)

  correus_per_enviar = []

  for idx, fila in df_f.iterrows():
    if pd.notna(fila["DATA_FINAL_DT"]) and fila["DATA_FINAL_DT"] == DATA_AVUI:
      email_dest = ""
      if "USUARI_XTEC" in fila and pd.notna(fila["USUARI_XTEC"]):
        u = str(fila["USUARI_XTEC"]).strip()
        email_dest = u if "@" in u else f"{u}@xtec.cat"
      elif "NOM_MAIL" in fila and pd.notna(fila["NOM_MAIL"]):
        email_dest = str(fila["NOM_MAIL"]).strip()

      codi_act = str(fila["CODI_ACTIVITAT"]).strip()
      id_unic = f"AVAL_FORM_{codi_act}_{email_dest}"

      if email_dest and id_unic not in df_log["ID_UNICI"].values:
        codi_nom = f"{codi_act} {fila['NOM_ACTIVITAT']}"
        correus_per_enviar.append({
            "ID_UNICI": id_unic,
            "Destinatari": email_dest,
            "Activitat": codi_nom,
            "Assumpte": f"Avaluació activitat de formació: {codi_nom}",
            "Cos": (
                "Benvolgut/da,\n\nT'enviem les instruccions per avaluar"
                f" l'activitat formativa {codi_nom}.\n\nL'equip del CRP"
            ),
        })

  print(
      f"🔍 Trobats {len(correus_per_enviar)} correus per enviar per a la data"
      f" d'avui ({DATA_AVUI})."
  )
  enviar_correus_smtp(correus_per_enviar)
else:
  print("⚠️ No s'ha trobat el fitxer Formadors.csv amb la columna DATA_INICI.")
