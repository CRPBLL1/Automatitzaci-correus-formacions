from datetime import datetime, timedelta
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import glob
import os
import smtplib
import pandas as pd

# Servidor SMTP (Canvia si no fas servir XTEC)
SMTP_SERVER = "smtp.xtec.cat"
SMTP_PORT = 587
SENDER_EMAIL = os.environ.get("EMAIL_USER")
SENDER_PASSWORD = os.environ.get("EMAIL_PASS")

LOG_FILE = "enviats_log.csv"
DIES_RECORDATORI = 7
DATA_AVUI = datetime.today().date()

# Carregar o crear el fitxer log de control
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
    df.columns = df.columns.str.strip()
    return df


def parse_data(data_str):
    if pd.isna(data_str):
        return None
    data_str = str(data_str).strip()
    try:
        return datetime.strptime(data_str, "%d/%m/%y").date()
    except ValueError:
        try:
            return datetime.strptime(data_str, "%d/%m/%Y").date()
        except ValueError:
            return None


def enviar_correus_smtp(llista_correus):
    if not llista_correus:
        print("ℹ️ No hi ha correus pendents per enviar avui.")
        return

    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print(
            "❌ Error: No s'han trobat les credencials EMAIL_USER o EMAIL_PASS."
        )
        return

    enviats_exit = []
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)

        for item in llista_correus:
            msg = MIMEMultipart()
            msg["From"] = SENDER_EMAIL
            msg["To"] = item["Destinatari"]
            msg["Subject"] = item["Assumpte"]
            msg.attach(MIMEText(item["Cos"], "plain"))

            server.send_message(msg)
            print(
                f"✅ Enviat correu a {item['Destinatari']} - {item['Assumpte']}"
            )

            enviats_exit.append(
                {
                    "ID_UNICI": item["ID_UNICI"],
                    "TIPUS_CORREU": item["ID_UNICI"].split("_")[0],
                    "CODI_ACTIVITAT": item["Activitat"].split()[0],
                    "DESTINATARI": item["Destinatari"],
                    "DATA_ENVIAMENT": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                }
            )

        server.quit()

        # Actualitzar el log i guardar a disc
        global df_log
        df_nous = pd.DataFrame(enviats_exit)
        df_log = pd.concat([df_log, df_nous], ignore_index=True)
        df_log.to_csv(LOG_FILE, index=False)
        print(f"🎉 Procés finalitzat: {len(enviats_exit)} correus enviats.")

    except Exception as e:
        print(f"❌ Error durant l'enviament de correus: {e}")


# Buscar automàticament els fitxers CSV al repositori
fitxers_csv = glob.glob("*.csv")
fitxer_formadors = next(
    (f for f in fitxers_csv if "Formador" in f or "Extracc" in f), None
)
fitxer_matriculacions = next(
    (f for f in fitxers_csv if "Matricul" in f or "Extracc" in f), None
)

if fitxer_formadors and fitxer_matriculacions:
    df_f = netejar_dataframe(
        pd.read_csv(fitxer_formadors, encoding="latin1", sep=";")
    )
    df_m = netejar_dataframe(
        pd.read_csv(fitxer_matriculacions, encoding="latin1", sep=";")
    )

    df_f["DATA_INICI_DT"] = df_f["DATA_INICI"].apply(parse_data)
    df_f["DATA_FINAL_DT"] = df_f["DATA_FINAL"].apply(parse_data)

    df_activitats = df_f[
        ["CODI_ACTIVITAT", "NOM_ACTIVITAT", "DATA_INICI_DT", "DATA_FINAL_DT"]
    ].drop_duplicates(subset=["CODI_ACTIVITAT"])
    df_m_complet = pd.merge(
        df_m, df_activitats, on="CODI_ACTIVITAT", how="left"
    )

    correus_per_enviar = []

    # 1. Recordatori Formadors
    for idx, fila in df_f.iterrows():
        if (
            pd.notna(fila["DATA_INICI_DT"])
            and (fila["DATA_INICI_DT"] - timedelta(days=DIES_RECORDATORI))
            == DATA_AVUI
        ):
            email_dest = (
                f"{fila['USUARI_XTEC']}@xtec.cat"
                if pd.notna(fila["USUARI_XTEC"])
                else ""
            )
            id_unic = f"REC_FORM_{fila['CODI_ACTIVITAT']}_{email_dest}"
            if id_unic not in df_log["ID_UNICI"].values and email_dest:
                codi_nom = f"{fila['CODI_ACTIVITAT']} {fila['NOM_ACTIVITAT']}"
                correus_per_enviar.append(
                    {
                        "ID_UNICI": id_unic,
                        "Destinatari": email_dest,
                        "Activitat": codi_nom,
                        "Assumpte": f"Recordatori: inici de l'activitat {codi_nom}",
                        "Cos": f"Hola {fila['NOM_PERSONA']},\n\nEt recordem que l'activitat {codi_nom} comença el dia {fila['DATA_INICI_DT'].strftime('%d/%m/%Y')}.\n\nL'equip del CRP",
                    }
                )

    # 2. Avaluació Formadors
    for idx, fila in df_f.iterrows():
        if (
            pd.notna(fila["DATA_FINAL_DT"])
            and fila["DATA_FINAL_DT"] == DATA_AVUI
        ):
            email_dest = (
                f"{fila['USUARI_XTEC']}@xtec.cat"
                if pd.notna(fila["USUARI_XTEC"])
                else ""
            )
            id_unic = f"AVAL_FORM_{fila['CODI_ACTIVITAT']}_{email_dest}"
            if id_unic not in df_log["ID_UNICI"].values and email_dest:
                codi_nom = f"{fila['CODI_ACTIVITAT']} {fila['NOM_ACTIVITAT']}"
                correus_per_enviar.append(
                    {
                        "ID_UNICI": id_unic,
                        "Destinatari": email_dest,
                        "Activitat": codi_nom,
                        "Assumpte": f"Avaluació activitat de formació: {codi_nom}",
                        "Cos": f"Benvolgut/da,\n\nT'enviem les instruccions per avaluar {codi_nom}.\n\nL'equip del CRP",
                    }
                )

    # 3. Recordatori Participants
    df_admesos = df_m_complet[df_m_complet["IND_ASSIGNACIO"] == "S"]
    for idx, fila in df_admesos.iterrows():
        if (
            pd.notna(fila["DATA_INICI_DT"])
            and (fila["DATA_INICI_DT"] - timedelta(days=DIES_RECORDATORI))
            == DATA_AVUI
        ):
            email_dest = fila["NOM_MAIL"]
            id_unic = f"REC_PART_{fila['CODI_ACTIVITAT']}_{email_dest}"
            if id_unic not in df_log["ID_UNICI"].values and email_dest:
                codi_nom = f"{fila['CODI_ACTIVITAT']} {fila['NOM_ACTIVITAT']}"
                correus_per_enviar.append(
                    {
                        "ID_UNICI": id_unic,
                        "Destinatari": email_dest,
                        "Activitat": codi_nom,
                        "Assumpte": f"Recordatori: inici de l'activitat {codi_nom}",
                        "Cos": f"Hola {fila['NOM']},\n\nEt recordem que l'activitat {codi_nom} comença el dia {fila['DATA_INICI_DT'].strftime('%d/%m/%Y')}.\n\nL'equip del CRP",
                    }
                )

    # 4. Avaluació Participants
    for idx, fila in df_admesos.iterrows():
        if (
            pd.notna(fila["DATA_FINAL_DT"])
            and fila["DATA_FINAL_DT"] == DATA_AVUI
        ):
            email_dest = fila["NOM_MAIL"]
            id_unic = f"AVAL_PART_{fila['CODI_ACTIVITAT']}_{email_dest}"
            if id_unic not in df_log["ID_UNICI"].values and email_dest:
                codi_nom = f"{fila['CODI_ACTIVITAT']} {fila['NOM_ACTIVITAT']}"
                correus_per_enviar.append(
                    {
                        "ID_UNICI": id_unic,
                        "Destinatari": email_dest,
                        "Activitat": codi_nom,
                        "Assumpte": f"Avaluació activitat de formació {codi_nom}",
                        "Cos": f"Benvolgut/da,\n\nT'enviem les instruccions per avaluar {codi_nom}.\n\nL'equip del CRP",
                    }
                )

    enviar_correus_smtp(correus_per_enviar)
else:
    print("⚠️ Cal pujar els fitxers CSV de Formadors i Matriculacions.")
