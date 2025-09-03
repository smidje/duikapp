import streamlit as st
import pandas as pd
from pathlib import Path
import datetime
import io

# ==== Bestanden ====
DUIKERS_FILE = "duikers.xlsx"
PLACES_FILE = "duikplaatsen.xlsx"
DUIKEN_FILE = "duiken.xlsx"
LOGO_FILE = "logo.jpg"

# ==== Helper opslag ====
def init_file(file, columns):
    path = Path(file)
    if not path.exists():
        df = pd.DataFrame(columns=columns)
        df.to_excel(file, index=False, engine="xlsxwriter")
    return pd.read_excel(file, engine="openpyxl")

def save_file(file, df):
    df.to_excel(file, index=False, engine="xlsxwriter")

@st.cache_data(show_spinner=False)
def load_duikers():
    return init_file(DUIKERS_FILE, ["Naam"])

@st.cache_data(show_spinner=False)
def load_places():
    return init_file(PLACES_FILE, ["Plaats"])

@st.cache_data(show_spinner=False)
def load_duiken():
    return init_file(DUIKEN_FILE, ["Datum", "Plaats", "Duiker"])

def refresh_caches():
    load_duikers.clear()
    load_places.clear()
    load_duiken.clear()

# ==== Auth ====
def check_login(username, password):
    return username == "admin" and password == "1234"

def login_page():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: url('{LOGO_FILE}') no-repeat center center fixed;
            background-size: cover;
        }}
        .login-box {{
            background: rgba(255, 255, 255, 0.88);
            padding: 2rem;
            border-radius: 18px;
            width: 360px;
            margin: auto;
            margin-top: 12vh;
            backdrop-filter: blur(2px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }}
        .login-title {{
            margin: 0 0 10px 0;
            font-weight: 700;
            letter-spacing: .3px;
        }}
        .footer-note {{
            margin-top: 10px;
            font-size: 12px;
            opacity: .75;
        }}
        </style>
        """, unsafe_allow_html=True
    )
    st.markdown("<div class='login-box'><h2 class='login-title'>ANWW Duikapp</h2><p>Log in om verder te gaan</p>", unsafe_allow_html=True)
    username = st.text_input("Gebruikersnaam", key="user")
    password = st.text_input("Wachtwoord", type="password", key="pw")
    if st.button("Login", type="primary", use_container_width=True):
        if check_login(username, password):
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Ongeldige login")
    st.markdown("<div class='footer-note'>Tip: admin / 1234</div></div>", unsafe_allow_html=True)

# ==== UI Chrome ====
def header():
    st.markdown(
        f"""
        <style>
        .app-header {{
            display:flex; align-items:center; gap:12px; padding: 10px 0 0 0;
        }}
        .app-header img {{
            height: 48px; border-radius: 8px;
        }}
        .app-title {{
            margin:0; font-size: 24px; font-weight: 700;
        }}
        </style>
        <div class="app-header">
            <img src="{LOGO_FILE}" alt="logo" />
            <h2 class="app-title">ANWW Duikapp</h2>
        </div>
        """,
        unsafe_allow_html=True
    )

# ==== Pagina's ====
def page_duiken():
    header()
    st.subheader("Nieuwe duik registreren")

    duikers_df = load_duikers().copy()
    places_df = load_places().copy()

    plaatsen = places_df["Plaats"].dropna().astype(str).tolist() if not places_df.empty else []
    duikers_lijst = duikers_df["Naam"].dropna().astype(str).tolist() if not duikers_df.empty else []

    col1, col2 = st.columns(2)
    with col1:
        datum = st.date_input("Datum", datetime.date.today())
    with col2:
        if plaatsen:
            plaats = st.selectbox("Duikplaats", plaatsen, index=0)
        else:
            st.info("Nog geen duikplaatsen. Voeg er hieronder één toe.")
            plaats = ""

    with st.expander("Duikplaats toevoegen", expanded=(len(plaatsen) == 0)):
        nieuwe_plaats = st.text_input("Nieuwe duikplaats")
        if st.button("Voeg duikplaats toe"):
            if nieuwe_plaats and nieuwe_plaats not in plaatsen:
                places_df.loc[len(places_df)] = [nieuwe_plaats]
                save_file(PLACES_FILE, places_df)
                refresh_caches()
                st.success(f"Duikplaats '{nieuwe_plaats}' toegevoegd.")
                st.rerun()
            else:
                st.warning("Voer een unieke naam in.")

    geselecteerde_duikers = st.multiselect("Kies duikers", duikers_lijst, help="Selecteer één of meerdere duikers")
    nieuwe_duiker = st.text_input("Nieuwe duiker toevoegen")
    if st.button("Voeg duiker toe"):
        if nieuwe_duiker and nieuwe_duiker not in duikers_lijst:
            duikers_df.loc[len(duikers_df)] = [nieuwe_duiker]
            save_file(DUIKERS_FILE, duikers_df)
            refresh_caches()
            st.success(f"Duiker '{nieuwe_duiker}' toegevoegd.")
            st.rerun()
        else:
            st.warning("Voer een unieke naam in.")

    if st.button("Opslaan duik(en)", type="primary", disabled=(not plaats or len(geselecteerde_duikers) == 0)):
        duiken_df = load_duiken().copy()
        for naam in geselecteerde_duikers:
            duiken_df.loc[len(duiken_df)] = [datum, plaats, naam]
        duiken_df["Datum"] = pd.to_datetime(duiken_df["Datum"]).dt.date
        save_file(DUIKEN_FILE, duiken_df)
        refresh_caches()
        st.success(f"{len(geselecteerde_duikers)} duik(en) opgeslagen voor {plaats} op {datum}.")

def page_overzicht():
    header()
    st.subheader("Overzicht duiken")

    df = load_duiken().copy()
    if df.empty:
        st.info("Nog geen duiken geregistreerd.")
        return

    df["Datum"] = pd.to_datetime(df["Datum"]).dt.date

    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        min_d = df["Datum"].min()
        max_d = df["Datum"].max()
        daterange = st.date_input("Datumrange", (min_d, max_d))
    with c2:
        plaatsen = ["Alle"] + sorted(df["Plaats"].dropna().unique().tolist())
        plaats_filter = st.selectbox("Duikplaats", plaatsen, index=0)
    with c3:
        duikers = ["Alle"] + sorted(df["Duiker"].dropna().unique().tolist())
        duiker_filter = st.selectbox("Duiker", duikers, index=0)

    f = df.copy()
    start, end = daterange if isinstance(daterange, tuple) else (df["Datum"].min(), df["Datum"].max())
    f = f[(f["Datum"] >= start) & (f["Datum"] <= end)]
    if plaats_filter != "Alle":
        f = f[f["Plaats"] == plaats_filter]
    if duiker_filter != "Alle":
        f = f[f["Duiker"] == duiker_filter]

    f = f.sort_values(["Datum", "Plaats", "Duiker"])
    st.dataframe(f, use_container_width=True, hide_index=True)

    st.download_button("Download CSV", data=f.to_csv(index=False).encode("utf-8"), file_name="duiken_export.csv", mime="text/csv")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        f.to_excel(writer, index=False, sheet_name="Duiken")
    st.download_button("Download Excel", data=output.getvalue(), file_name="duiken_export.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def page_beheer():
    header()
    st.subheader("Beheer lijsten")

    st.markdown("### Duikers")
    duikers_df = load_duikers().copy()
    st.dataframe(duikers_df, use_container_width=True, hide_index=True)
    new_d = st.text_input("Nieuwe duiker naam")
    if st.button("Toevoegen aan duikers"):
        if new_d and (new_d not in duikers_df["Naam"].astype(str).tolist()):
            duikers_df.loc[len(duikers_df)] = [new_d]
            save_file(DUIKERS_FILE, duikers_df)
            refresh_caches()
            st.success(f"Duiker '{new_d}' toegevoegd.")
            st.rerun()
        else:
            st.warning("Leeg of al bestaand.")

    st.markdown("---")
    st.markdown("### Duikplaatsen")
    places_df = load_places().copy()
    st.dataframe(places_df, use_container_width=True, hide_index=True)
    new_p = st.text_input("Nieuwe duikplaats")
    if st.button("Toevoegen aan duikplaatsen"):
        if new_p and (new_p not in places_df["Plaats"].astype(str).tolist()):
            places_df.loc[len(places_df)] = [new_p]
            save_file(PLACES_FILE, places_df)
            refresh_caches()
            st.success(f"Duikplaats '{new_p}' toegevoegd.")
            st.rerun()
        else:
            st.warning("Leeg of al bestaand.")

# ==== Main ====
def main():
    st.set_page_config(page_title="ANWW Duikapp", layout="wide")
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_page()
        return

    tabs = st.tabs(["Duiken invoeren", "Overzicht", "Beheer lijsten"])
    with tabs[0]:
        page_duiken()
    with tabs[1]:
        page_overzicht()
    with tabs[2]:
        page_beheer()

if __name__ == "__main__":
    main()
