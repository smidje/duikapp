import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, date
import hashlib, secrets

# ---------- Config ----------
st.set_page_config(page_title="Duiklogboek ANWW", page_icon="🐠", layout="wide")

DATA_DIR = Path(".")
DUIKERS_FILE = DATA_DIR / "Duikers ANWW.xlsx"
PLAATSEN_FILE = DATA_DIR / "Duikplaatsen Zeeland.xlsx"
LOG_FILE = DATA_DIR / "Duiklogboek.xlsx"
USERS_FILE = DATA_DIR / "users.csv"

# ---------- Helpers: hashing ----------
def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

def verify_password(password: str, salt: str, password_hash: str) -> bool:
    return hash_password(password, salt) == password_hash

def new_salt() -> str:
    return secrets.token_hex(16)

# ---------- Data IO ----------
@st.cache_data(ttl=10)
def load_duikers() -> pd.DataFrame:
    df = pd.read_excel(DUIKERS_FILE)
    # Verwacht één kolom met namen
    first_col = df.columns[0]
    df = df.rename(columns={first_col: "Duiker"})
    df["Duiker"] = df["Duiker"].astype(str).str.strip()
    df = df.dropna().drop_duplicates().sort_values("Duiker").reset_index(drop=True)
    return df

@st.cache_data(ttl=10)
def load_plaatsen() -> pd.DataFrame:
    df = pd.read_excel(PLAATSEN_FILE)
    first_col = df.columns[0]
    df = df.rename(columns={first_col: "Duikplaats"})
    df["Duikplaats"] = df["Duikplaats"].astype(str).str.strip()
    df = df.dropna().drop_duplicates().sort_values("Duikplaats").reset_index(drop=True)
    return df

@st.cache_data(ttl=5)
def load_log() -> pd.DataFrame:
    if LOG_FILE.exists():
        df = pd.read_excel(LOG_FILE)
        # Normaliseer kolommen
        if "Datum" in df.columns:
            df["Datum"] = pd.to_datetime(df["Datum"]).dt.date
        expected = ["Datum", "Duikplaats", "Duiker", "Opmerkingen", "IngevoerdDoor", "Tijdstempel"]
        for c in expected:
            if c not in df.columns:
                df[c] = None
        df = df[expected]
    else:
        df = pd.DataFrame(columns=["Datum", "Duikplaats", "Duiker", "Opmerkingen", "IngevoerdDoor", "Tijdstempel"])
    return df

def save_duikers(df: pd.DataFrame):
    st.cache_data.clear()
    df_out = df[["Duiker"]].rename(columns={"Duiker": "DUIKERS ANWW"})
    df_out.to_excel(DUIKERS_FILE, index=False)

def save_plaatsen(df: pd.DataFrame):
    st.cache_data.clear()
    df_out = df[["Duikplaats"]].rename(columns={"Duikplaats": "duikplaatsen ANWW"})
    df_out.to_excel(PLAATSEN_FILE, index=False)

def append_log(row: dict):
    st.cache_data.clear()
    df = load_log()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_excel(LOG_FILE, index=False)

def save_log(df: pd.DataFrame):
    st.cache_data.clear()
    df.to_excel(LOG_FILE, index=False)

@st.cache_data(ttl=5)
def load_users() -> pd.DataFrame:
    if USERS_FILE.exists():
        return pd.read_csv(USERS_FILE)
    else:
        return pd.DataFrame(columns=["username", "name", "role", "salt", "password_hash", "created_at"])

def save_users(df: pd.DataFrame):
    st.cache_data.clear()
    df.to_csv(USERS_FILE, index=False)

# ---------- Auth ----------
def login_form():
    st.subheader("Inloggen")
    username = st.text_input("Gebruikersnaam")
    password = st.text_input("Wachtwoord", type="password")
    ok = st.button("Inloggen", type="primary")
    if ok:
        users = load_users()
        row = users[users["username"] == username]
        if len(row) == 1:
            salt = row["salt"].iloc[0]
            pw_hash = row["password_hash"].iloc[0]
            if verify_password(password, salt, pw_hash):
                st.session_state["auth_user"] = {
                    "username": username,
                    "name": row["name"].iloc[0],
                    "role": row["role"].iloc[0],
                }
                st.success(f"Ingelogd als {row['name'].iloc[0]}")
                st.rerun()
            else:
                st.error("Onjuiste gebruikersnaam of wachtwoord.")
        else:
            st.error("Onjuiste gebruikersnaam of wachtwoord.")

def require_login():
    if "auth_user" not in st.session_state:
        login_form()
        st.stop()

def is_admin() -> bool:
    return st.session_state.get("auth_user", {}).get("role") == "admin"

# ---------- UI: Sidebar ----------
def sidebar_menu():
    with st.sidebar:
        st.title("🐠 Duiklogboek")
        if "auth_user" in st.session_state:
            user = st.session_state["auth_user"]
            st.caption(f"Ingelogd als **{user['name']}** ({user['username']})")
            choice = st.radio(
                "Navigatie",
                ["Duiken registreren", "Overzicht", "Afrekening", "Beheer"],
                captions=[
                    "Voeg nieuwe logregels toe",
                    "Bekijk/exporteer het logboek",
                    "Bereken vergoeding per duiker",
                    "Beheer lijsten en gebruikers",
                ],
            )
            if st.button("Uitloggen"):
                st.session_state.clear()
                st.rerun()
        else:
            choice = None
        return choice

# ---------- Pages ----------
def page_register():
    st.header("Duiken registreren")
    duikers = load_duikers()
    plaatsen = load_plaatsen()
    if duikers.empty:
        st.warning("Er staan nog geen duikers in de lijst.")
    if plaatsen.empty:
        st.warning("Er staan nog geen duikplaatsen in de lijst.")

    with st.form("reg_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            d = st.date_input("Datum", value=date.today(), format="DD-MM-YYYY")
        with col2:
            duiker = st.selectbox("Duiker", duikers["Duiker"].tolist())
        with col3:
            plaats = st.selectbox("Duikplaats", plaatsen["Duikplaats"].tolist())
        opmerkingen = st.text_area("Opmerkingen", placeholder="Optioneel")
        submitted = st.form_submit_button("Opslaan", type="primary")
        if submitted:
            row = {
                "Datum": d,
                "Duikplaats": plaats,
                "Duiker": duiker,
                "Opmerkingen": opmerkingen if opmerkingen else None,
                "IngevoerdDoor": st.session_state["auth_user"]["username"],
                "Tijdstempel": datetime.utcnow().isoformat()
            }
            append_log(row)
            st.success("Duik geregistreerd.")

def page_overview():
    st.header("Overzicht")
    df = load_log()
    if df.empty:
        st.info("Nog geen logregels.")
        return

    # Filters
    colf1, colf2, colf3, colf4 = st.columns(4)
    with colf1:
        vanaf = st.date_input("Vanaf", value=df["Datum"].min() or date.today(), format="DD-MM-YYYY")
    with colf2:
        tot = st.date_input("Tot en met", value=df["Datum"].max() or date.today(), format="DD-MM-YYYY")
    with colf3:
        duiker_filter = st.selectbox("Duiker (filter)", ["(Alle)"] + sorted(df["Duiker"].dropna().unique().tolist()))
    with colf4:
        plaats_filter = st.selectbox("Duikplaats (filter)", ["(Alle)"] + sorted(df["Duikplaats"].dropna().unique().tolist()))

    mask = (df["Datum"] >= vanaf) & (df["Datum"] <= tot)
    if duiker_filter != "(Alle)":
        mask &= df["Duiker"] == duiker_filter
    if plaats_filter != "(Alle)":
        mask &= df["Duikplaats"] == plaats_filter

    view = df.loc[mask].copy()
    view = view.sort_values(["Datum", "Duikplaats", "Duiker"]).reset_index(drop=True)
    st.dataframe(view, use_container_width=True)

    # Export
    c1, c2 = st.columns([1,1])
    with c1:
        if st.button("Exporteren naar Excel (filter)", type="secondary"):
            xls = view.to_excel(index=False)
    with c2:
        if st.button("Hele logboek downloaden", type="secondary"):
            pass

    # Provide download buttons
    from io import BytesIO
    b1 = BytesIO()
    view.to_excel(b1, index=False)
    st.download_button("⬇️ Download gefilterde selectie (Excel)", data=b1.getvalue(), file_name="Duiklogboek_selectie.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    b2 = BytesIO()
    df.to_excel(b2, index=False)
    st.download_button("⬇️ Download volledig logboek (Excel)", data=b2.getvalue(), file_name="Duiklogboek.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def page_afrekening():
    st.header("Afrekening")
    df = load_log()
    if df.empty:
        st.info("Nog geen logregels.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        vanaf = st.date_input("Vanaf", value=df["Datum"].min() or date.today(), format="DD-MM-YYYY", key="afr_vanaf")
    with col2:
        tot = st.date_input("Tot en met", value=df["Datum"].max() or date.today(), format="DD-MM-YYYY", key="afr_tot")
    with col3:
        vergoeding = st.number_input("Vergoeding per duik (€)", min_value=0.0, step=1.0, value=5.0)

    mask = (df["Datum"] >= vanaf) & (df["Datum"] <= tot)
    selectie = df.loc[mask].copy()
    if selectie.empty:
        st.warning("Geen duiken in de gekozen periode.")
        return

    # Telling per duiker
    per_duiker = selectie.groupby("Duiker").size().reset_index(name="AantalDuiken")
    per_duiker["Bedrag"] = per_duiker["AantalDuiken"] * vergoeding
    per_duiker = per_duiker.sort_values(["Duiker"]).reset_index(drop=True)

    st.subheader("Resultaat per duiker")
    st.dataframe(per_duiker, use_container_width=True)

    totaal = per_duiker["Bedrag"].sum()
    st.metric("Totaal uit te keren", f"€ {totaal:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # Download afrekening
    from io import BytesIO
    b = BytesIO()
    with pd.ExcelWriter(b, engine="openpyxl") as writer:
        per_duiker.to_excel(writer, sheet_name="Afrekening", index=False)
        selectie.sort_values(["Datum", "Duikplaats", "Duiker"]).to_excel(writer, sheet_name="Detail", index=False)
    st.download_button("⬇️ Download Afrekening (Excel)", data=b.getvalue(), file_name="Afrekening.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def page_beheer():
    st.header("Beheer")
    tabs = st.tabs(["Duikers", "Duikplaatsen", "Gebruikers"])

    # --- Duikers ---
    with tabs[0]:
        st.subheader("Duikerslijst")
        df = load_duikers()
        st.dataframe(df, use_container_width=True, height=300)
        with st.form("add_duiker", clear_on_submit=True):
            name = st.text_input("Nieuwe duiker toevoegen")
            ok = st.form_submit_button("Toevoegen", type="primary")
            if ok and name.strip():
                new = pd.DataFrame([{"Duiker": name.strip()}])
                df2 = pd.concat([df, new]).drop_duplicates().sort_values("Duiker").reset_index(drop=True)
                save_duikers(df2)
                st.success(f"Duiker '{name}' toegevoegd.")
                st.rerun()

    # --- Duikplaatsen ---
    with tabs[1]:
        st.subheader("Duikplaatsenlijst")
        df = load_plaatsen()
        st.dataframe(df, use_container_width=True, height=300)
        with st.form("add_plaats", clear_on_submit=True):
            plaats = st.text_input("Nieuwe duikplaats toevoegen")
            ok = st.form_submit_button("Toevoegen", type="primary")
            if ok and plaats.strip():
                new = pd.DataFrame([{"Duikplaats": plaats.strip()}])
                df2 = pd.concat([df, new]).drop_duplicates().sort_values("Duikplaats").reset_index(drop=True)
                save_plaatsen(df2)
                st.success(f"Duikplaats '{plaats}' toegevoegd.")
                st.rerun()

    # --- Gebruikers ---
    with tabs[2]:
        if not is_admin():
            st.warning("Alleen beheerders kunnen gebruikers beheren.")
        else:
            st.subheader("Gebruikers")
            users = load_users()
            st.dataframe(users[["username", "name", "role", "created_at"]], use_container_width=True, height=300)

            st.markdown("### Nieuwe gebruiker")
            with st.form("add_user", clear_on_submit=True):
                u = st.text_input("Gebruikersnaam")
                n = st.text_input("Naam")
                role = st.selectbox("Rol", ["user", "admin"])
                pw1 = st.text_input("Wachtwoord", type="password")
                pw2 = st.text_input("Wachtwoord (herhaal)", type="password")
                ok = st.form_submit_button("Aanmaken", type="primary")
                if ok:
                    if not u or not n or not pw1:
                        st.error("Vul alle velden in.")
                    elif pw1 != pw2:
                        st.error("Wachtwoorden komen niet overeen.")
                    elif u in users["username"].tolist():
                        st.error("Gebruikersnaam bestaat al.")
                    else:
                        s = new_salt()
                        h = hash_password(pw1, s)
                        new_row = {
                            "username": u,
                            "name": n,
                            "role": role,
                            "salt": s,
                            "password_hash": h,
                            "created_at": datetime.utcnow().isoformat(),
                        }
                        users = pd.concat([users, pd.DataFrame([new_row])], ignore_index=True)
                        save_users(users)
                        st.success(f"Gebruiker '{u}' aangemaakt.")

            st.markdown("### Wachtwoord wijzigen")
            with st.form("change_pw", clear_on_submit=True):
                u2 = st.selectbox("Gebruiker", users["username"].tolist())
                newpw1 = st.text_input("Nieuw wachtwoord", type="password")
                newpw2 = st.text_input("Nieuw wachtwoord (herhaal)", type="password")
                ok2 = st.form_submit_button("Wijzigen")
                if ok2:
                    if newpw1 != newpw2 or not newpw1:
                        st.error("Wachtwoorden komen niet overeen of leeg.")
                    else:
                        s = new_salt()
                        h = hash_password(newpw1, s)
                        users.loc[users["username"] == u2, ["salt", "password_hash"]] = [s, h]
                        save_users(users)
                        st.success(f"Wachtwoord voor '{u2}' gewijzigd.")

# ---------- App ----------
def main():
    # Warm up data files if nodig
    for p, template in [
        (DUIKERS_FILE, pd.DataFrame({"DUIKERS ANWW": []})),
        (PLAATSEN_FILE, pd.DataFrame({"duikplaatsen ANWW": []})),
        (LOG_FILE, pd.DataFrame(columns=["Datum", "Duikplaats", "Duiker", "Opmerkingen", "IngevoerdDoor", "Tijdstempel"])),
        (USERS_FILE, pd.DataFrame(columns=["username", "name", "role", "salt", "password_hash", "created_at"])),
    ]:
        if not p.exists():
            if p.suffix == ".xlsx":
                template.to_excel(p, index=False)
            else:
                template.to_csv(p, index=False)

    # Auth gate
    if "auth_user" not in st.session_state:
        login_form()
        st.stop()

    page = sidebar_menu()
    if page == "Duiken registreren":
        page_register()
    elif page == "Overzicht":
        page_overview()
    elif page == "Afrekening":
        page_afrekening()
    elif page == "Beheer":
        page_beheer()
    else:
        st.write("Kies een pagina in het menu.")

if __name__ == "__main__":
    main()
