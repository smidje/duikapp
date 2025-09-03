
import streamlit as st
import pandas as pd
from pathlib import Path
import datetime
import io

USERS_FILE  = "users.xlsx"
DUIKERS_FILE = "duikers.xlsx"
PLACES_FILE  = "duikplaatsen.xlsx"
DUIKEN_FILE  = "duiken.xlsx"
LOGO_FILE    = "logo.jpg"

st.set_page_config(page_title="ANWW Duikapp", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --primary:#2563eb;
        --bg:#f7f9fc;
        --card:#ffffff;
        --text:#0f172a;
        --muted:#6b7280;
        --border:#e5e7eb;
    }
    .stApp { background: var(--bg); }
    .app-card { background: var(--card); border:1px solid var(--border);
        border-radius:16px; padding:18px; box-shadow: 0 8px 24px rgba(2,6,23,0.06); }
    .app-header { display:flex; align-items:center; gap:14px; padding: 6px 0 12px 0; }
    .app-header img {height:52px; border-radius:10px;}
    .app-title {margin:0; font-size:26px; font-weight:800; color:var(--text);}
    </style>
    """, unsafe_allow_html=True
)

def init_file(file, columns, defaults=None):
    path = Path(file)
    if not path.exists():
        if defaults is not None:
            df = pd.DataFrame(defaults, columns=columns)
        else:
            df = pd.DataFrame(columns=columns)
        df.to_excel(file, index=False, engine="openpyxl")
    return pd.read_excel(file, engine="openpyxl")

def save_file(file, df):
    df.to_excel(file, index=False, engine="openpyxl")

@st.cache_data(show_spinner=False)
def load_users():
    return init_file(USERS_FILE, ["Username","Password","Role"], defaults=[["admin","1234","admin"]])

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
    load_users.clear(); load_duikers.clear(); load_places.clear(); load_duiken.clear()

def check_login(username, password):
    users = load_users()
    match = users[(users["Username"].astype(str)==str(username)) & (users["Password"].astype(str)==str(password))]
    if not match.empty:
        return match.iloc[0]["Role"]
    return None

def login_page():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: url('{LOGO_FILE}') no-repeat center center fixed !important;
            background-size: cover !important;
        }}
        .login-box {{
            background: rgba(255,255,255,0.88);
            padding: 2rem;
            border-radius: 18px;
            width: 360px;
            margin: auto;
            margin-top: 12vh;
            backdrop-filter: blur(2px);
            box-shadow: 0 10px 30px rgba(2,6,23,0.25);
        }}
        .login-title {{ margin:0 0 12px 0; font-weight:800; letter-spacing:.2px; }}
        </style>
        """, unsafe_allow_html=True
    )
    st.markdown("<div class='login-box app-card'><h2 class='login-title'>ANWW Duikapp</h2><p>Log in om verder te gaan</p>", unsafe_allow_html=True)
    username = st.text_input("Gebruikersnaam", key="login_user")
    password = st.text_input("Wachtwoord", type="password", key="login_pw")
    if st.button("Login", type="primary", use_container_width=True, key="login_btn"):
        role = check_login(username, password)
        if role is not None:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = role
            st.rerun()
        else:
            st.error("Ongeldige login")
    st.markdown("</div>", unsafe_allow_html=True)

def header():
    st.markdown(
        f"""
        <div class="app-header">
            <img src="{LOGO_FILE}" alt="logo" />
            <h2 class="app-title">ANWW Duikapp</h2>
        </div>
        """,
        unsafe_allow_html=True
    )
    c1, c2, c3 = st.columns([6,2,2])
    with c2:
        st.write(f"Ingelogd als **{st.session_state.get('username','?')}** ({st.session_state.get('role','?')})")
    with c3:
        if st.button("Uitloggen", key="logout_btn"):
            st.session_state.clear()
            st.rerun()

def page_duiken():
    header()
    st.markdown("### Nieuwe duik registreren")
    duikers_df = load_duikers().copy(); places_df = load_places().copy()
    plaatsen = places_df["Plaats"].dropna().astype(str).tolist() if not places_df.empty else []
    duikers_lijst = duikers_df["Naam"].dropna().astype(str).tolist() if not duikers_df.empty else []

    c1,c2 = st.columns(2)
    with c1:
        datum = st.date_input("Datum", datetime.date.today(), key="duiken_datum", format="DD/MM/YYYY")
    with c2:
        plaats = st.selectbox("Duikplaats", plaatsen, index=0 if len(plaatsen)>0 else None, key="duiken_plaats") if plaatsen else ""

    with st.expander("Duikplaats toevoegen", expanded=(len(plaatsen)==0)):
        nieuwe_plaats = st.text_input("Nieuwe duikplaats", key="duiken_nieuwe_plaats")
        if st.button("Voeg duikplaats toe", key="duiken_btn_plaats_toevoegen"):
            if nieuwe_plaats and nieuwe_plaats not in plaatsen:
                places_df.loc[len(places_df)] = [nieuwe_plaats]; save_file(PLACES_FILE, places_df)
                refresh_caches(); st.success(f"Duikplaats '{nieuwe_plaats}' toegevoegd."); st.rerun()
            else: st.warning("Voer een unieke naam in.")

    geselecteerde_duikers = st.multiselect("Kies duikers", duikers_lijst, key="duiken_sel_duikers")
    nieuwe_duiker = st.text_input("Nieuwe duiker toevoegen", key="duiken_nieuwe_duiker")
    if st.button("Voeg duiker toe", key="duiken_btn_duiker_toevoegen"):
        if nieuwe_duiker and nieuwe_duiker not in duikers_lijst:
            duikers_df.loc[len(duikers_df)] = [nieuwe_duiker]; save_file(DUIKERS_FILE, duikers_df)
            refresh_caches(); st.success(f"Duiker '{nieuwe_duiker}' toegevoegd."); st.rerun()
        else: st.warning("Voer een unieke naam in.")

    disabled = (not plaats) or (len(geselecteerde_duikers)==0)
    if st.button("Opslaan duik(en)", type="primary", disabled=disabled, key="duiken_opslaan"):
        duiken_df = load_duiken().copy()
        for naam in geselecteerde_duikers:
            duiken_df.loc[len(duiken_df)] = [datum, plaats, naam]
        duiken_df["Datum"] = pd.to_datetime(duiken_df["Datum"]).dt.date
        save_file(DUIKEN_FILE, duiken_df); refresh_caches()
        st.success(f"{len(geselecteerde_duikers)} duik(en) opgeslagen voor {plaats} op {datum.strftime('%d/%m/%Y')}.")

def page_overzicht():
    header()
    st.markdown("### Overzicht duiken")
    df = load_duiken().copy()
    if df.empty: st.info("Nog geen duiken geregistreerd."); return
    df["Datum"] = pd.to_datetime(df["Datum"]).dt.date

    c1,c2,c3 = st.columns([1,1,2])
    with c1:
        min_d, max_d = df["Datum"].min(), df["Datum"].max()
        daterange = st.date_input("Datumrange", (min_d, max_d), key="overzicht_range", format="DD/MM/YYYY")
    with c2:
        plaatsen = ["Alle"] + sorted(df["Plaats"].dropna().unique().tolist())
        plaats_filter = st.selectbox("Duikplaats", plaatsen, index=0, key="overzicht_plaats")
    with c3:
        duikers = ["Alle"] + sorted(df["Duiker"].dropna().unique().tolist())
        duiker_filter = st.selectbox("Duiker", duikers, index=0, key="overzicht_duiker")

    f = df.copy()
    start,end = daterange if isinstance(daterange, tuple) else (df["Datum"].min(), df["Datum"].max())
    f = f[(f["Datum"]>=start)&(f["Datum"]<=end)]
    if plaats_filter!="Alle": f = f[f["Plaats"]==plaats_filter]
    if duiker_filter!="Alle": f = f[f["Duiker"]==duiker_filter]
    f = f.sort_values(["Datum","Plaats","Duiker"])

    view = f.copy()
    view["Datum"] = pd.to_datetime(view["Datum"]).dt.strftime("%d/%m/%Y")

    st.markdown("<div class='app-card'>", unsafe_allow_html=True); st.dataframe(view, use_container_width=True, hide_index=True); st.markdown("</div>", unsafe_allow_html=True)

    st.download_button("Download CSV", data=f.to_csv(index=False).encode("utf-8"),
                       file_name="duiken_export.csv", mime="text/csv", key="overzicht_csv")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        f.to_excel(writer, index=False, sheet_name="Duiken")
    st.download_button("Download Excel", data=output.getvalue(), file_name="duiken_export.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="overzicht_xlsx")

def page_afrekening():
    header()
    st.markdown("### Afrekening per duiker")
    df = load_duiken().copy()
    if df.empty: st.info("Nog geen duiken geregistreerd."); return
    df["Datum"] = pd.to_datetime(df["Datum"]).dt.date

    c1,c2,c3 = st.columns(3)
    with c1:
        min_d, max_d = df["Datum"].min(), df["Datum"].max()
        daterange = st.date_input("Periode", (min_d, max_d), key="afr_range", format="DD/MM/YYYY")
    with c2:
        vergoeding = st.number_input("Bedrag per duik (€)", min_value=0.0, step=1.0, value=5.0, key="afr_bedrag")
    with c3:
        plaats_filter = st.selectbox("Duikplaats (optioneel)", ["Alle"] + sorted(df["Plaats"].dropna().unique().tolist()), index=0, key="afr_plaats")

    start,end = daterange if isinstance(daterange, tuple) else (df["Datum"].min(), df["Datum"].max())
    mask = (df["Datum"]>=start)&(df["Datum"]<=end)
    if plaats_filter!="Alle": mask &= df["Plaats"]==plaats_filter
    selectie = df.loc[mask].copy()
    if selectie.empty: st.warning("Geen duiken in de gekozen periode/filters."); return

    per_duiker = selectie.groupby("Duiker").size().reset_index(name="AantalDuiken")
    per_duiker["Bedrag"] = (per_duiker["AantalDuiken"]*vergoeding).round(2)
    per_duiker = per_duiker.sort_values("Duiker").reset_index(drop=True)

    st.markdown("<div class='app-card'>", unsafe_allow_html=True); st.dataframe(per_duiker, use_container_width=True, hide_index=True); st.markdown("</div>", unsafe_allow_html=True)
    totaal = per_duiker["Bedrag"].sum()
    st.metric("Totaal uit te keren", f"€ {totaal:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

    xbuf = io.BytesIO()
    with pd.ExcelWriter(xbuf, engine="openpyxl") as writer:
        per_duiker.to_excel(writer, index=False, sheet_name="Afrekening")
        selectie.sort_values(["Datum","Plaats","Duiker"]).to_excel(writer, index=False, sheet_name="Detail")
    st.download_button("⬇️ Download Afrekening (Excel)", data=xbuf.getvalue(), file_name="Afrekening.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="afr_xlsx")

def page_beheer():
    header()
    st.markdown("### Beheer")

    tabs = st.tabs(["Gebruikers", "Duikers", "Duikplaatsen", "Backup"])

    with tabs[0]:
        users_df = load_users().copy()
        st.dataframe(users_df, use_container_width=True, hide_index=True)
        c1,c2,c3 = st.columns(3)
        with c1:
            u = st.text_input("Nieuwe gebruiker (username)", key="beheer_u_name")
        with c2:
            p = st.text_input("Wachtwoord", key="beheer_u_pwd")
        with c3:
            r = st.selectbox("Rol", ["user","admin"], index=0, key="beheer_u_role")
        if st.button("Gebruiker toevoegen", key="beheer_btn_user_add"):
            if u and p and (u not in users_df["Username"].astype(str).tolist()):
                users_df.loc[len(users_df)] = [u,p,r]; save_file(USERS_FILE, users_df); refresh_caches()
                st.success(f"Gebruiker '{u}' toegevoegd."); st.rerun()
            else:
                st.warning("Ongeldig of reeds bestaand.")

    with tabs[1]:
        duikers_df = load_duikers().copy()
        st.dataframe(duikers_df, use_container_width=True, hide_index=True)
        new_d = st.text_input("Nieuwe duiker naam", key="beheer_nieuwe_duiker")
        if st.button("Toevoegen aan duikers", key="beheer_btn_duiker_toevoegen"):
            if new_d and (new_d not in duikers_df["Naam"].astype(str).tolist()):
                duikers_df.loc[len(duikers_df)] = [new_d]; save_file(DUIKERS_FILE, duikers_df)
                refresh_caches(); st.success(f"Duiker '{new_d}' toegevoegd."); st.rerun()
            else: st.warning("Leeg of al bestaand.")

    with tabs[2]:
        places_df = load_places().copy()
        st.dataframe(places_df, use_container_width=True, hide_index=True)
        new_p = st.text_input("Nieuwe duikplaats", key="beheer_nieuwe_plaats")
        if st.button("Toevoegen aan duikplaatsen", key="beheer_btn_plaats_toevoegen"):
            if new_p and (new_p not in places_df["Plaats"].astype(str).tolist()):
                places_df.loc[len(places_df)] = [new_p]; save_file(PLACES_FILE, places_df)
                refresh_caches(); st.success(f"Duikplaats '{new_p}' toegevoegd."); st.rerun()
            else: st.warning("Leeg of al bestaand.")

    with tabs[3]:
        st.markdown("Maak een zip-backup van alle Excel-bestanden.")
        import zipfile, os
        if st.button("Maak backup (zip)", key="beheer_backup_make"):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as zipf:
                for f in [USERS_FILE, DUIKERS_FILE, PLACES_FILE, DUIKEN_FILE]:
                    if Path(f).exists(): zipf.write(f, os.path.basename(f))
            st.download_button("Download duikapp_backup.zip", data=buffer.getvalue(),
                               file_name="duikapp_backup.zip", mime="application/zip", key="beheer_backup_dl")

def main():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        login_page(); return

    tabs = st.tabs(["Duiken invoeren","Overzicht","Afrekening","Beheer"])
    with tabs[0]: page_duiken()
    with tabs[1]: page_overzicht()
    with tabs[2]: page_afrekening()
    with tabs[3]: page_beheer()

if __name__ == "__main__":
    main()
