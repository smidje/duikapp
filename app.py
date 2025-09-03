
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
    :root { --primary:#2563eb; --bg:#f7f9fc; --card:#ffffff; --text:#0f172a; --border:#e5e7eb; }
    .stApp { background: var(--bg); }
    .app-header { display:flex; align-items:center; gap:14px; padding: 6px 0 12px 0; }
    .app-header img {height:52px; border-radius:10px;}
    .app-title {margin:0; font-size:26px; font-weight:800; color:var(--text);}
    </style>
    """, unsafe_allow_html=True
)

def init_file(file, columns, defaults=None):
    p = Path(file)
    if not p.exists():
        df = pd.DataFrame(defaults, columns=columns) if defaults is not None else pd.DataFrame(columns=columns)
        df.to_excel(file, index=False, engine="openpyxl")
    return pd.read_excel(file, engine="openpyxl")

def save_file(file, df):
    df.to_excel(file, index=False, engine="openpyxl")

@st.cache_data(show_spinner=False)
def load_users(): return init_file(USERS_FILE, ["Username","Password","Role"], defaults=[["admin","1234","admin"]])
@st.cache_data(show_spinner=False)
def load_duikers(): return init_file(DUIKERS_FILE, ["Naam"])
@st.cache_data(show_spinner=False)
def load_places(): return init_file(PLACES_FILE, ["Plaats"])
@st.cache_data(show_spinner=False)
def load_duiken(): return init_file(DUIKEN_FILE, ["Datum","Plaats","Duiker"])

def refresh_all():
    load_users.clear(); load_duikers.clear(); load_places.clear(); load_duiken.clear()

def login_page():
    st.markdown(f"""
    <style>
    .stApp {{ background: url('{LOGO_FILE}') no-repeat center center fixed !important; background-size: cover !important; }}
    .login-box {{ background: rgba(255,255,255,.9); padding: 2rem; border-radius: 16px; width: 360px; margin: 12vh auto; }}
    </style>""", unsafe_allow_html=True)
    st.markdown("<div class='login-box'><h2>ANWW Duikapp</h2><p>Log in</p>", unsafe_allow_html=True)
    u = st.text_input("Gebruikersnaam", key="login_user")
    p = st.text_input("Wachtwoord", type="password", key="login_pw")
    if st.button("Login", type="primary", use_container_width=True, key="login_btn"):
        users = load_users()
        m = users[(users["Username"].astype(str)==str(u)) & (users["Password"].astype(str)==str(p))]
        if not m.empty:
            st.session_state.logged_in = True
            st.session_state.username = u
            st.session_state.role = m.iloc[0]["Role"]
            st.rerun()
        else:
            st.error("Ongeldige login")
    st.markdown("</div>", unsafe_allow_html=True)

def header(suffix: str):
    st.markdown(f"""
    <div class="app-header">
        <img src="{LOGO_FILE}" alt="logo" />
        <h2 class="app-title">ANWW Duikapp</h2>
    </div>""", unsafe_allow_html=True)
    c1,c2,c3 = st.columns([6,2,2])
    with c2:
        st.write(f"Ingelogd als **{st.session_state.get('username','?')}**")
    with c3:
        if st.button("Uitloggen", key=f"logout_btn_{suffix}"):
            st.session_state.clear(); st.rerun()

def page_duiken():
    header("duiken")
    duikers_df = load_duikers().copy(); places_df = load_places().copy()
    plaatsen = places_df["Plaats"].dropna().astype(str).tolist() if not places_df.empty else []
    duikers = duikers_df["Naam"].dropna().astype(str).tolist() if not duikers_df.empty else []
    c1,c2 = st.columns(2)
    with c1: datum = st.date_input("Datum", datetime.date.today(), key="duiken_datum", format="DD/MM/YYYY")
    with c2: plaats = st.selectbox("Duikplaats", plaatsen, index=0 if plaatsen else None, key="duiken_plaats") if plaatsen else ""
    with st.expander("Duikplaats toevoegen", expanded=(len(plaatsen)==0)):
        np = st.text_input("Nieuwe duikplaats", key="duiken_nieuwe_plaats")
        if st.button("Voeg duikplaats toe", key="duiken_btn_plaats_toevoegen"):
            if np and np not in plaatsen:
                places_df.loc[len(places_df)] = [np]; save_file(PLACES_FILE, places_df); refresh_all(); st.success(f"Duikplaats '{np}' toegevoegd."); st.rerun()
            else: st.warning("Voer een unieke naam in.")
    sel = st.multiselect("Kies duikers", duikers, key="duiken_sel_duikers")
    nd = st.text_input("Nieuwe duiker toevoegen", key="duiken_nieuwe_duiker")
    if st.button("Voeg duiker toe", key="duiken_btn_duiker_toevoegen"):
        if nd and nd not in duikers:
            duikers_df.loc[len(duikers_df)] = [nd]; save_file(DUIKERS_FILE, duikers_df); refresh_all(); st.success(f"Duiker '{nd}' toegevoegd."); st.rerun()
        else: st.warning("Voer een unieke naam in.")
    if st.button("Opslaan duik(en)", type="primary", disabled=(not plaats or len(sel)==0), key="duiken_opslaan"):
        duiken_df = load_duiken().copy()
        for naam in sel: duiken_df.loc[len(duiken_df)] = [datum, plaats, naam]
        duiken_df["Datum"] = pd.to_datetime(duiken_df["Datum"]).dt.date
        save_file(DUIKEN_FILE, duiken_df); refresh_all()
        st.success(f"{len(sel)} duik(en) opgeslagen voor {plaats} op {datum.strftime('%d/%m/%Y')}.")

def page_overzicht():
    header("overzicht")
    df = load_duiken().copy()
    if df.empty: st.info("Nog geen duiken geregistreerd."); return
    df["Datum"] = pd.to_datetime(df["Datum"]).dt.date
    c1,c2,c3 = st.columns([1,1,2])
    with c1:
        min_d,max_d = df["Datum"].min(), df["Datum"].max()
        rng = st.date_input("Datumrange", (min_d,max_d), key="overzicht_range", format="DD/MM/YYYY")
    with c2:
        plaatsen = ["Alle"] + sorted(df["Plaats"].dropna().unique().tolist())
        pf = st.selectbox("Duikplaats", plaatsen, index=0, key="overzicht_plaats")
    with c3:
        duikers = ["Alle"] + sorted(df["Duiker"].dropna().unique().tolist())
        dfilt = st.selectbox("Duiker", duikers, index=0, key="overzicht_duiker")
    start,end = rng if isinstance(rng, tuple) else (df["Datum"].min(), df["Datum"].max())
    f = df[(df["Datum"]>=start)&(df["Datum"]<=end)].copy()
    if pf!="Alle": f = f[f["Plaats"]==pf]
    if dfilt!="Alle": f = f[f["Duiker"]==dfilt]
    f = f.sort_values(["Datum","Plaats","Duiker"])
    view = f.copy(); view["Datum"] = pd.to_datetime(view["Datum"]).dt.strftime("%d/%m/%Y")
    st.dataframe(view, use_container_width=True, hide_index=True, key="overzicht_table")
    st.download_button("Download CSV", data=f.to_csv(index=False).encode("utf-8"),
        file_name="duiken_export.csv", mime="text/csv", key="overzicht_csv")
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w: f.to_excel(w, index=False, sheet_name="Duiken")
    st.download_button("Download Excel", data=out.getvalue(), file_name="duiken_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="overzicht_xlsx")

def page_afrekening():
    header("afrekening")
    df = load_duiken().copy()
    if df.empty: st.info("Nog geen duiken geregistreerd."); return
    df["Datum"] = pd.to_datetime(df["Datum"]).dt.date
    c1,c2,c3 = st.columns(3)
    with c1:
        min_d,max_d = df["Datum"].min(), df["Datum"].max()
        rng = st.date_input("Periode", (min_d,max_d), key="afr_range", format="DD/MM/YYYY")
    with c2:
        bedrag = st.number_input("Bedrag per duik (€)", min_value=0.0, step=1.0, value=5.0, key="afr_bedrag")
    with c3:
        pf = st.selectbox("Duikplaats (optioneel)", ["Alle"] + sorted(df["Plaats"].dropna().unique().tolist()), index=0, key="afr_plaats")
    start,end = rng if isinstance(rng, tuple) else (df["Datum"].min(), df["Datum"].max())
    m = (df["Datum"]>=start)&(df["Datum"]<=end)
    if pf!="Alle": m &= df["Plaats"]==pf
    s = df.loc[m].copy()
    if s.empty: st.warning("Geen duiken in de gekozen periode/filters."); return
    per = s.groupby("Duiker").size().reset_index(name="AantalDuiken")
    per["Bedrag"] = (per["AantalDuiken"]*bedrag).round(2)
    st.dataframe(per, use_container_width=True, hide_index=True, key="afr_table")
    total = per["Bedrag"].sum()
    st.metric("Totaal uit te keren", f"€ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        per.to_excel(w, index=False, sheet_name="Afrekening")
        s.sort_values(["Datum","Plaats","Duiker"]).to_excel(w, index=False, sheet_name="Detail")
    st.download_button("⬇️ Download Afrekening (Excel)", data=out.getvalue(), file_name="Afrekening.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="afr_xlsx")

def page_beheer():
    header("beheer")
    tabs = st.tabs(["Gebruikers","Duikers","Duikplaatsen","Backup"])
    with tabs[0]:
        users = load_users().copy()
        st.dataframe(users, use_container_width=True, hide_index=True, key="users_table")
        c1,c2,c3 = st.columns(3)
        with c1: u = st.text_input("Nieuwe gebruiker (username)", key="beheer_u_name")
        with c2: p = st.text_input("Wachtwoord", key="beheer_u_pwd")
        with c3: r = st.selectbox("Rol", ["user","admin"], index=0, key="beheer_u_role")
        if st.button("Gebruiker toevoegen", key="beheer_btn_user_add"):
            if u and p and (u not in users["Username"].astype(str).tolist()):
                users.loc[len(users)] = [u,p,r]; save_file(USERS_FILE, users); refresh_all(); st.success(f"Gebruiker '{u}' toegevoegd."); st.rerun()
            else: st.warning("Ongeldig of reeds bestaand.")
    with tabs[1]:
        duikers = load_duikers().copy()
        st.dataframe(duikers, use_container_width=True, hide_index=True, key="duikers_table")
        nd = st.text_input("Nieuwe duiker naam", key="beheer_nieuwe_duiker")
        if st.button("Toevoegen aan duikers", key="beheer_btn_duiker_toevoegen"):
            if nd and (nd not in duikers["Naam"].astype(str).tolist()):
                duikers.loc[len(duikers)] = [nd]; save_file(DUIKERS_FILE, duikers); refresh_all(); st.success(f"Duiker '{nd}' toegevoegd."); st.rerun()
            else: st.warning("Leeg of al bestaand.")
    with tabs[2]:
        places = load_places().copy()
        st.dataframe(places, use_container_width=True, hide_index=True, key="places_table")
        np = st.text_input("Nieuwe duikplaats", key="beheer_nieuwe_plaats")
        if st.button("Toevoegen aan duikplaatsen", key="beheer_btn_plaats_toevoegen"):
            if np and (np not in places["Plaats"].astype(str).tolist()):
                places.loc[len(places)] = [np]; save_file(PLACES_FILE, places); refresh_all(); st.success(f"Duikplaats '{np}' toegevoegd."); st.rerun()
            else: st.warning("Leeg of al bestaand.")
    with tabs[3]:
        st.write("Maak een zip-backup van alle Excel-bestanden.")
        import zipfile, os
        if st.button("Maak backup (zip)", key="beheer_backup_make"):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                for f in [USERS_FILE, DUIKERS_FILE, PLACES_FILE, DUIKEN_FILE]:
                    if Path(f).exists(): z.write(f, os.path.basename(f))
            st.download_button("Download duikapp_backup.zip", data=buf.getvalue(), file_name="duikapp_backup.zip",
                mime="application/zip", key="beheer_backup_dl")

def main():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in: login_page(); return
    tabs = st.tabs(["Duiken invoeren","Overzicht","Afrekening","Beheer"])
    with tabs[0]: page_duiken()
    with tabs[1]: page_overzicht()
    with tabs[2]: page_afrekening()
    with tabs[3]: page_beheer()

if __name__ == "__main__":
    main()
