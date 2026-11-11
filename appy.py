from datetime import datetime, timedelta
import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Gestor de Correus de Formació", page_icon="✉️", layout="wide"
)

st.title("✉️ Automatització i Gestió de Correus de Formació")
st.markdown(
    "Carrega els fitxers d'extracció per generar els correus evitant duplicitats."
)

# --- ARCHIU DE LOG / REGISTRE D'ENVIAMENTS ---
LOG_FILE = "enviats_log.csv"

# Carregar o crear el registre d'enviats
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

# --- PANEL LATERAL ---
st.sidebar.header("1. Càrrega de fitxers CSV")
file_formadors = st.sidebar.file_uploader(
    "Fitxer Formadors (CSV)", type=["csv"]
)
file_matriculacions = st.sidebar.file_uploader(
    "Fitxer Matriculacions (CSV)", type=["csv"]
)

st.sidebar.header("2. Paràmetres d'enviament")
dies_recordatori = st.sidebar.number_input(
    "Dies d'antelació per als recordatoris", min_value=1, max_value=30, value=7
)
data_referencia = st.sidebar.date_input(
    "Data d'execució / enviament", datetime.today()
)

st.sidebar.header("3. Control de Duplicats")
evitar_duplicats = st.sidebar.checkbox(
    "Filtra i exclou correus ja enviats", value=True
)
st.sidebar.caption(
    f"Total de correus en l'històric d'enviats: {len(df_log)}"
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


if file_formadors and file_matriculacions:
    df_f = netejar_dataframe(pd.read_csv(file_formadors, encoding="latin1", sep=";"))
    df_m = netejar_dataframe(pd.read_csv(file_matriculacions, encoding="latin1", sep=";"))

    df_f["DATA_INICI_DT"] = df_f["DATA_INICI"].apply(parse_data)
    df_f["DATA_FINAL_DT"] = df_f["DATA_FINAL"].apply(parse_data)

    df_activitats = df_f[
        ["CODI_ACTIVITAT", "NOM_ACTIVITAT", "DATA_INICI_DT", "DATA_FINAL_DT"]
    ].drop_duplicates(subset=["CODI_ACTIVITAT"])

    df_m_complet = pd.merge(df_m, df_activitats, on="CODI_ACTIVITAT", how="left")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "👨‍🏫 1. Recordatori Formadors",
            "📝 2. Avaluació Formadors",
            "👨‍🎓 3. Recordatori Participants",
            "📋 4. Avaluació Participants",
            "📜 Històric d'Enviats",
        ]
    )

    # Llista global per registrar enviaments realitzats en la sessió
    nous_enviaments = []

    # --- TAB 1: RECORDATORI FORMADORS ---
    with tab1:
        st.subheader("Recordatoris a Formadors")
        correus = []
        for idx, fila in df_f.iterrows():
            if pd.isna(fila["DATA_INICI_DT"]):
                continue

            if fila["DATA_INICI_DT"] - timedelta(days=dies_recordatori) == data_referencia:
                email = f"{fila['USUARI_XTEC']}@xtec.cat" if pd.notna(fila["USUARI_XTEC"]) else ""
                codi_act = fila["CODI_ACTIVITAT"]
                id_unic = f"REC_FORM_{codi_act}_{email}"

                if evitar_duplicats and id_unic in df_log["ID_UNICI"].values:
                    continue  # Si ja s'ha enviat, s'omet

                codi_nom = f"{codi_act} {fila['NOM_ACTIVITAT']}"
                nom_complet = f"{fila['NOM_PERSONA']} {fila['COGNOM1']}"
                data_inici_fmt = fila["DATA_INICI_DT"].strftime("%d/%m/%Y")

                correus.append({
                    "ID_UNICI": id_unic,
                    "Destinatari": email,
                    "Formador/a": nom_complet,
                    "Activitat": codi_nom,
                    "Assumpte": f"Recordatori: inici de l'activitat {codi_nom} en la qual fas de formador/a.",
                    "Cos": f"Hola, {nom_complet} ,\n\nEt recordem que l’activitat de formació {codi_nom} en què col·labores com a persona formadora, comença el pròxim {data_inici_fmt}.\n\nUn dels primers passos és revisar la llista de participants i obtenir el full de signatures per a fer el seguiment de l’assistència.\n\nAquesta documentació estarà disponible 20 dies abans de la data prevista d’inici de l’activitat.\n\nEn el document: https://serveiseducatius.xtec.cat/baixllobregat1/formacio/manual-persones-formadores/, trobaràs tota la informació necessària per a fer-ho i també per fer el tancament de l'activitat quan arribi el moment.\n\nSi a l’activitat hi ha més d'una persona formadora, poseu-vos d'acord, amb una que ho faci n'hi ha prou.\n\nTrobaràs tota la informació sobre les activitats de formació de la nostra zona a: https://serveiseducatius.xtec.cat/baixllobregat1/formacio/pla-de-formacio-de-zona-pfz/\n\nPer a qualsevol dubte o aclariment pots adreçar-te al CRP al correu crp-santfeliu@xtec.cat o bé al telèfon 936 853 100\n\nGràcies per la teva col·laboració\n\nL'equip del CRP"
                })

        df_res = pd.DataFrame(correus)
        st.write(f"**Correus pendents d'enviar:** {len(df_res)}")
        st.dataframe(df_res, use_container_width=True)

    # --- TAB 2: AVALUACIÓ FORMADORS ---
    with tab2:
        st.subheader("Avaluació Final per a Formadors")
        correus = []
        for idx, fila in df_f.iterrows():
            if pd.isna(fila["DATA_FINAL_DT"]):
                continue

            if fila["DATA_FINAL_DT"] == data_referencia:
                email = f"{fila['USUARI_XTEC']}@xtec.cat" if pd.notna(fila["USUARI_XTEC"]) else ""
                codi_act = fila["CODI_ACTIVITAT"]
                id_unic = f"AVAL_FORM_{codi_act}_{email}"

                if evitar_duplicats and id_unic in df_log["ID_UNICI"].values:
                    continue

                codi_nom = f"{codi_act} {fila['NOM_ACTIVITAT']}"
                data_limit_fmt = (fila["DATA_FINAL_DT"] + timedelta(days=30)).strftime("%d/%m/%Y")

                correus.append({
                    "ID_UNICI": id_unic,
                    "Destinatari": email,
                    "Activitat": codi_nom,
                    "Assumpte": f"Avaluació activitat de formació: {codi_nom}",
                    "Cos": f"Benvolguda,\nBenvolgut,\n\nT'enviem les instruccions per realitzar l'avaluació de l’activitat formativa {codi_nom}, a la que has participat com a formador.\n\nEl qüestionari estarà obert fins al dia {data_limit_fmt}. Recorda que és indispensable fer aquest darrer pas per poder certificar l'activitat.\n \nInstruccions:\n1. Entrar al GTAF https://aplicacions.ensenyament.gencat.cat/pls/gtaf/inici\n    (Amb l’identificador i contrasenya de la XTEC)\n2. Clicar a Formadors/es, col·laboradors, suport\n3. Clicar a Qüestionaris\n4. Seleccionar el qüestionari de l’activitat.\n5. Respondre el qüestionari\n6. Enviar\nMOLT IMPORTANT: cal prémer el botó ENVIAR perquè es registri el qüestionari.\nUna vegada el qüestionari ha estat enviat desapareix el botó que hi dona accés.\n\nEn aquest mateix enllaç, un cop finalitzat el període de respostes, podreu consultar el resum de les valoracions dels participants en l’activitat.\n\nMoltes gràcies per la teva col·laboració,\n\nL’equip del CRP"
                })

        df_res = pd.DataFrame(correus)
        st.write(f"**Correus pendents d'enviar:** {len(df_res)}")
        st.dataframe(df_res, use_container_width=True)

    # --- TAB 3: RECORDATORI PARTICIPANTS ---
    with tab3:
        st.subheader("Recordatoris a Participants Admesos")
        df_admesos = df_m_complet[df_m_complet["IND_ASSIGNACIO"] == "S"]
        correus = []
        for idx, fila in df_admesos.iterrows():
            if pd.isna(fila["DATA_INICI_DT"]):
                continue

            if fila["DATA_INICI_DT"] - timedelta(days=dies_recordatori) == data_referencia:
                email = fila["NOM_MAIL"]
                codi_act = fila["CODI_ACTIVITAT"]
                id_unic = f"REC_PART_{codi_act}_{email}"

                if evitar_duplicats and id_unic in df_log["ID_UNICI"].values:
                    continue

                codi_nom = f"{codi_act} {fila['NOM_ACTIVITAT']}"
                nom_complet = f"{fila['NOM']} {fila['COGNOM1']}" if pd.notna(fila["COGNOM1"]) else fila["NOM"]
                data_inici_fmt = fila["DATA_INICI_DT"].strftime("%d/%m/%Y")

                correus.append({
                    "ID_UNICI": id_unic,
                    "Destinatari": email,
                    "Participant": nom_complet,
                    "Activitat": codi_nom,
                    "Assumpte": f"Recordatori: inici de l'activitat {codi_nom}",
                    "Cos": f"Hola, {nom_complet},\n\nEt recordem que l’activitat de formació {codi_nom} a la que t'has inscrit com a assistent, comença el pròxim {data_inici_fmt}\n\nPer a més informació podeu consultar la descripció de l’activitat cercant-la en aquest enllaç: https://ja.cat/pfz2627\n\nSalutacions,\n\nL'equip del CRP"
                })

        df_res = pd.DataFrame(correus)
        st.write(f"**Correus pendents d'enviar:** {len(df_res)}")
        st.dataframe(df_res, use_container_width=True)

    # --- TAB 4: AVALUACIÓ PARTICIPANTS ---
    with tab4:
        st.subheader("Avaluació Final per a Participants Admesos")
        df_admesos = df_m_complet[df_m_complet["IND_ASSIGNACIO"] == "S"]
        correus = []
        for idx, fila in df_admesos.iterrows():
            if pd.isna(fila["DATA_FINAL_DT"]):
                continue

            if fila["DATA_FINAL_DT"] == data_referencia:
                email = fila["NOM_MAIL"]
                codi_act = fila["CODI_ACTIVITAT"]
                id_unic = f"AVAL_PART_{codi_act}_{email}"

                if evitar_duplicats and id_unic in df_log["ID_UNICI"].values:
                    continue

                codi_nom = f"{codi_act} {fila['NOM_ACTIVITAT']}"
                data_limit_fmt = (fila["DATA_FINAL_DT"] + timedelta(days=30)).strftime("%d/%m/%Y")

                correus.append({
                    "ID_UNICI": id_unic,
                    "Destinatari": email,
                    "Activitat": codi_nom,
                    "Assumpte": f"Avaluació activitat de formació {codi_nom}",
                    "Cos": f"Benvolguda,\nBenvolgut,\n\nT'enviem les instruccions per avaluar l’activitat formativa {codi_nom}, a la que has participat.\n\nEl qüestionari estarà obert fins el dia {data_limit_fmt}. Recorda que és indispensable fer aquest darrer pas per poder certificar l'activitat.\nInstruccions:\n1. Has d’accedir amb el nom d'usuari i la contrasenya XTEC a la pàgina http://xtec.gencat.cat/ca/formacio/la-meva-formacio/les-meves-activitats/\n2. Aquesta pàgina et porta al resum de les activitats formatives a les quals estàs inscrit.\n3. Durant el període en què el qüestionari de l'activitat estigui actiu apareixerà el botó \"Qüestionari participants\", a la dreta de l'activitat, cal clicar per accedir-hi. \n4. Contesta les preguntes i MOLT IMPORTANT: cal prémer el botó ENVIAR perquè es registri el qüestionari. Una vegada el qüestionari ha estat enviat desapareix el botó que hi dóna accés.\nNota: La persona formadora pot consultar la llista de persones participants que ja han omplert el qüestionari, però no pot conèixer el contingut de les respostes donades, les respostes són anònimes. Les vostres valoracions seran recollides i ens serviran per millorar els cursos de cara a properes edicions.\n\nGràcies per la teva col·laboració.\nSalutacions,\nEquip de CRP"
                })

        df_res = pd.DataFrame(correus)
        st.write(f"**Correus pendents d'enviar:** {len(df_res)}")
        st.dataframe(df_res, use_container_width=True)

    # --- TAB 5: PESTANYA D'HISTÒRIC I REGISTRE ---
    with tab5:
        st.subheader("Històric d'enviament de correus")
        st.markdown("Aquí pots consultar la llista de tots els correus que ja s'han registrat com a enviats.")
        st.dataframe(df_log, use_container_width=True)

else:
    st.info("👈 Si us plau, carrega els dos fitxers CSV al menú lateral per començar.")