
import streamlit as st
import pandas as pd
from pathlib import Path
import datetime
from datetime import datetime as dt, timedelta
import io
import bcrypt
import uuid

USERS_FILE    = "users.xlsx"
DUIKERS_FILE  = "duikers.xlsx"
PLACES_FILE   = "duikplaatsen.xlsx"
DUIKEN_FILE   = "duiken.xlsx"
AUDIT_FILE    = "audit_log.xlsx"
LOGO_FILE     = "logo.jpg"

MAX_ATTEMPTS = 5
LOCK_MINUTES = 15

st.set_page_config(page_title="ANWW Duikapp", layout="wide")

# Minimal, robust styles (avoid complex HTML that might break render)
st.markdown("""
    <style>
    .stApp { background: #f7f9fc; }
    .appbar { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
    .badge { border:1px solid #e5e7eb; padding:4px 8px; border-radius:999px; font-size:0.9rem; background:#fff; }
    .logo { height:44px; border-radius:8px; }
    </style>
""", unsafe_allow_html=True)

def init_file(file, columns, defaults=None):
    p = Path(file)
    if not p.exists():
        df = pd.DataFrame(defaults, columns=columns) if defaults is not None else pd.DataFrame(columns=columns)
        df.to_excel(file, index=False, engine="openpyxl")
    return pd.read_excel(file, engine="openpyxl")

def save_file(file, df):
    df.to_excel(file, index=False, engine="openpyxl")

@st.cache_data(show_spinner=False)
def load_users():
    df = init_file(USERS_FILE, ["Username","Password","Role"], defaults=[["admin","1234","admin"]])
    for col, default in [("PasswordHash",""),("FailedAttempts",0),("LockedUntil","")]:
        if col not in df.columns: df[col] = default
    for col in ["Username","Password","PasswordHash","Role","FailedAttempts","LockedUntil"]:
        if col not in df.columns: df[col] = "" if col != "FailedAttempts" else 0
    return df[["Username","Password","PasswordHash","Role","FailedAttempts","LockedUntil"]]

def persist_users(df):
    out = df.copy()
    if "Password" in out.columns: out["Password"] = ""
    save_file(USERS_FILE, out[["Username","PasswordHash","Role","FailedAttempts","LockedUntil"]])

@st.cache_data(show_spinner=False)
def load_duikers(): return init_file(DUIKERS_FILE, ["Naam"])
@st.cache_data(show_spinner=False)
def load_places(): return init_file(PLACES_FILE, ["Plaats"])
@st.cache_data(show_spinner=False)
def load_duiken(): return init_file(DUIKEN_FILE, ["Datum","Plaats","Duiker"])
@st.cache_data(show_spinner=False)
def load_audit(): return init_file(AUDIT_FILE, ["TimestampUTC","User","Action","Details","SessionId"])

def append_audit(user, action, details=""):
    try:
        df = pd.read_excel(AUDIT_FILE, engine="openpyxl")
    except Exception:
        df = pd.DataFrame(columns=["TimestampUTC","User","Action","Details","SessionId"])
    row = {
        "TimestampUTC": dt.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "User": user or "",
        "Action": action,
        "Details": details,
        "SessionId": st.session_state.get("session_id","")
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_excel(AUDIT_FILE, index=False, engine="openpyxl")
    load_audit.clear()

def refresh_all():
    load_users.clear(); load_duikers.clear(); load_places.clear(); load_duiken.clear()

def verify_password(row, password: str) -> bool:
    ph = str(row.get("PasswordHash","") or "")
    if ph:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), ph.encode("utf-8"))
        except Exception:
            return False
    pw = str(row.get("Password","") or "")
    return pw == password

def set_password(users_df, username, new_password):
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    users_df.loc[users_df["Username"]==username, "PasswordHash"] = hashed
    if "Password" in users_df.columns: users_df.loc[users_df["Username"]==username, "Password"] = ""
    users_df.loc[users_df["Username"]==username, "FailedAttempts"] = 0
    users_df.loc[users_df["Username"]==username, "LockedUntil"] = ""
    persist_users(users_df); refresh_all()

def migrate_plaintext_to_hash(users_df, username, password):
    set_password(users_df, username, password)

def is_locked(row):
    lu = str(row.get("LockedUntil","") or "")
    if not lu: return False, None
    try:
        until = dt.fromisoformat(lu)
        if dt.utcnow() < until: return True, until
        else: return False, None
    except Exception:
        return False, None

def register_failed_attempt(users_df, username):
    users_df.loc[users_df["Username"]==username, "FailedAttempts"] = users_df.loc[users_df["Username"]==username, "FailedAttempts"].astype(int) + 1
    attempts = int(users_df.loc[users_df["Username"]==username, "FailedAttempts"].iloc[0])
    locked_until = ""
    if attempts >= MAX_ATTEMPTS:
        until = dt.utcnow() + timedelta(minutes=LOCK_MINUTES)
        locked_until = until.isoformat(timespec="seconds")
        users_df.loc[users_df["Username"]==username, "LockedUntil"] = locked_until
        users_df.loc[users_df["Username"]==username, "FailedAttempts"] = 0
        append_audit(username, "account_locked", f"until={locked_until}")
    persist_users(users_df); refresh_all()
    return attempts, locked_until

def clear_lock(users_df, username):
    users_df.loc[users_df["Username"]==username, "FailedAttempts"] = 0
    users_df.loc[users_df["Username"]==username, "LockedUntil"] = ""
    persist_users(users_df); refresh_all()

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
        if u not in users["Username"].astype(str).tolist():
            st.error("Onbekende gebruiker"); append_audit(u, "login_failed", "unknown_user")
        else:
            row = users[users["Username"]==u].iloc[0]
            locked, until = is_locked(row)
            if locked:
                st.error(f"Account geblokkeerd tot {until.strftime('%Y-%m-%d %H:%M:%S')} UTC.")
                append_audit(u, "login_blocked", f"locked_until={until.isoformat()}")
            else:
                if verify_password(row, p):
                    if str(row.get("Password","") or "") != "":
                        migrate_plaintext_to_hash(users, u, p); users = load_users(); row = users[users["Username"]==u].iloc[0]; append_audit(u, "password_migrated", "legacy->bcrypt")
                    clear_lock(users, u)
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    st.session_state.role = row["Role"]
                    append_audit(u, "login_success", f"role={row['Role']}")
                    st.rerun()
                else:
                    attempts, locked_until = register_failed_attempt(users, u)
                    if locked_until:
                        st.error(f"Teveel foute pogingen. Geblokkeerd tot {locked_until} UTC."); append_audit(u, "login_failed_locked", f"locked_until={locked_until}")
                    else:
                        left = MAX_ATTEMPTS - attempts
                        st.error(f"Onjuist wachtwoord. Nog {left} poging(en) over."); append_audit(u, "login_failed", f"attempts={attempts}")
    st.markdown("</div>", unsafe_allow_html=True)

def appbar(suffix: str):
    col1, col2, col3 = st.columns([6,2,2])
    with col1:
        st.markdown(f"<div class='appbar'><img class='logo' src='{LOGO_FILE}' /><strong>ANWW Duikapp</strong></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='badge'>{st.session_state.get('username','?')} · {st.session_state.get('role','?')}</div>", unsafe_allow_html=True)
    with col3:
        if st.button("Uitloggen", key=f"logout_{suffix}"):
            append_audit(st.session_state.get('username',''), "logout", "")
            st.session_state.clear(); st.rerun()

def page_duiken():
    appbar("duiken")
    role = st.session_state.get("role","user")
    duikers_df = load_duikers().copy(); places_df = load_places().copy()
    plaatsen = places_df["Plaats"].dropna().astype(str).tolist() if not places_df.empty else []
    duikers = duikers_df["Naam"].dropna().astype(str).tolist() if not duikers_df.empty else []
    c1,c2 = st.columns(2)
    with c1: datum = st.date_input("Datum", datetime.date.today(), key="duiken_datum", format="DD/MM/YYYY")
    with c2: plaats = st.selectbox("Duikplaats", plaatsen, index=0 if plaatsen else None, key="duiken_plaats") if plaatsen else ""
    if role == "admin":
        with st.expander("Duikplaats toevoegen", expanded=(len(plaatsen)==0)):
            np = st.text_input("Nieuwe duikplaats", key="duiken_nieuwe_plaats")
            if st.button("Voeg duikplaats toe", key="duiken_btn_plaats_toevoegen"):
                if np and np not in plaatsen:
                    places_df.loc[len(places_df)] = [np]; save_file(PLACES_FILE, places_df); refresh_all(); append_audit(st.session_state.get('username',''), "place_added", np); st.success(f"Duikplaats '{np}' toegevoegd."); st.rerun()
                else: st.warning("Voer een unieke naam in.")
    sel = st.multiselect("Kies duikers", duikers, key="duiken_sel_duikers")
    if role == "admin":
        nd = st.text_input("Nieuwe duiker toevoegen", key="duiken_nieuwe_duiker")
        if st.button("Voeg duiker toe", key="duiken_btn_duiker_toevoegen"):
            if nd and nd not in duikers:
                duikers_df.loc[len(duikers_df)] = [nd]; save_file(DUIKERS_FILE, duikers_df); refresh_all(); append_audit(st.session_state.get('username',''), "diver_added", nd); st.success(f"Duiker '{nd}' toegevoegd."); st.rerun()
            else: st.warning("Voer een unieke naam in.")
    if st.button("Opslaan duik(en)", type="primary", disabled=(not plaats or len(sel)==0), key="duiken_opslaan"):
        duiken_df = load_duiken().copy()
        for naam in sel: duiken_df.loc[len(duiken_df)] = [datum, plaats, naam]
        duiken_df["Datum"] = pd.to_datetime(duiken_df["Datum"]).dt.date
        save_file(DUIKEN_FILE, duiken_df); refresh_all(); append_audit(st.session_state.get('username',''), "dives_saved", f"{len(sel)} @ {plaats} on {datum.strftime('%d/%m/%Y')}"); st.success(f"{len(sel)} duik(en) opgeslagen.")

def page_overzicht():
    appbar("overzicht")
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
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w: f.to_excel(w, index=False, sheet_name="Duiken")
    st.download_button("Download CSV", data=f.to_csv(index=False).encode("utf-8"), file_name="duiken_export.csv", mime="text/csv", key="overzicht_csv")
    st.download_button("Download Excel", data=out.getvalue(), file_name="duiken_export.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="overzicht_xlsx")

def page_afrekening():
    appbar("afrekening")
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
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        per.to_excel(w, index=False, sheet_name="Afrekening")
        s.sort_values(["Datum","Plaats","Duiker"]).to_excel(w, index=False, sheet_name="Detail")
    st.download_button("⬇️ Download Afrekening (Excel)", data=out.getvalue(), file_name="Afrekening.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="afr_xlsx")

def page_profiel():
    appbar("profiel")
    st.markdown("### Profiel")
    st.write(f"Gebruiker: **{st.session_state.get('username','?')}** · Rol: **{st.session_state.get('role','?')}**")
    st.markdown("#### Wachtwoord wijzigen")
    with st.form(key="pw_change_form"):
        cur = st.text_input("Huidig wachtwoord", type="password", key="pw_cur")
        new1 = st.text_input("Nieuw wachtwoord", type="password", key="pw_new1")
        new2 = st.text_input("Bevestig nieuw wachtwoord", type="password", key="pw_new2")
        submitted = st.form_submit_button("Wijzig wachtwoord")
    if submitted:
        users = load_users().copy()
        u = st.session_state.get("username","")
        row = users[users["Username"]==u].iloc[0]
        if not verify_password(row, cur):
            st.error("Huidig wachtwoord klopt niet.")
        elif not new1 or new1 != new2:
            st.error("Nieuwe wachtwoorden zijn leeg of komen niet overeen.")
        else:
            set_password(users, u, new1)
            st.success("Wachtwoord succesvol gewijzigd.")

def page_beheer():
    appbar("beheer")
    if st.session_state.get("role","user") != "admin":
        st.error("Toegang geweigerd — alleen admins."); return
    tabs = st.tabs(["Gebruikers","Duikers","Duikplaatsen","Backup"])
    with tabs[0]:
        users = load_users().copy()
        st.dataframe(users[["Username","Role","FailedAttempts","LockedUntil"]], use_container_width=True, hide_index=True, key="users_table")
        st.subheader("Nieuwe gebruiker")
        c1,c2,c3 = st.columns(3)
        with c1: u = st.text_input("Username", key="beheer_u_name")
        with c2: p = st.text_input("Wachtwoord", key="beheer_u_pwd")
        with c3: r = st.selectbox("Rol", ["user","admin"], index=0, key="beheer_u_role")
        if st.button("Gebruiker toevoegen", key="beheer_btn_user_add"):
            if u and p and (u not in users["Username"].astype(str).tolist()):
                hashed = bcrypt.hashpw(p.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                new_row = pd.DataFrame([{"Username":u,"Password":"","PasswordHash":hashed,"Role":r,"FailedAttempts":0,"LockedUntil":""}])
                users = pd.concat([users, new_row], ignore_index=True)
                persist_users(users); refresh_all(); st.success(f"Gebruiker '{u}' toegevoegd."); st.rerun()
            else: st.warning("Ongeldig of reeds bestaand.")
        st.divider()
        st.subheader("Wachtwoord resetten / Deblokkeren")
        all_users = users["Username"].astype(str).tolist()
        sel_user = st.selectbox("Kies gebruiker", all_users, key="beheer_sel_user")
        new_pw = st.text_input("Nieuw wachtwoord", key="beheer_new_pw")
        colr1, colr2 = st.columns(2)
        with colr1:
            if st.button("Reset wachtwoord", key="beheer_btn_reset_pw"):
                if sel_user and new_pw:
                    set_password(users, sel_user, new_pw); st.success(f"Wachtwoord van '{sel_user}' is gewijzigd.")
                else: st.warning("Selecteer gebruiker en geef nieuw wachtwoord in.")
        with colr2:
            if st.button("Deblokkeer account", key="beheer_btn_unlock"):
                clear_lock(users, sel_user); st.success(f"Account van '{sel_user}' is gedeblokkeerd.")
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
        st.subheader("Backup (zip)")
        # Eenvoudiger en stabieler: 1 download button die bij klik de zip maakt
        import zipfile, os
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for f in [USERS_FILE, DUIKERS_FILE, PLACES_FILE, DUIKEN_FILE]:
                if Path(f).exists(): z.write(f, os.path.basename(f))
        st.download_button("⬇️ Download duikapp_backup.zip", data=buf.getvalue(),
                           file_name="duikapp_backup.zip", mime="application/zip", key="beheer_backup_dl")

def main():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in: login_page(); return
    role = st.session_state.get("role","user")
    if role == "admin":
        tabs = st.tabs(["Duiken invoeren","Overzicht","Afrekening","Profiel","Beheer"])
        with tabs[0]: page_duiken()
        with tabs[1]: page_overzicht()
        with tabs[2]: page_afrekening()
        with tabs[3]: page_profiel()
        with tabs[4]: page_beheer()
    else:
        tabs = st.tabs(["Duiken invoeren","Overzicht","Afrekening","Profiel"])
        with tabs[0]: page_duiken()
        with tabs[1]: page_overzicht()
        with tabs[2]: page_afrekening()
        with tabs[3]: page_profiel()

if __name__ == "__main__":
    main()
