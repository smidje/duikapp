# Duiklogboek Webapp (Phase 1)

Functies in deze versie:
- Inloggen (bestand `users.csv`, standaard gebruiker: **admin / admin** — wijzig dit meteen na inloggen).
- Lijsten beheren: duikers en duikplaatsen toevoegen (schrijft naar `Duikers ANWW.xlsx` en `Duikplaatsen Zeeland.xlsx`).
- Duiken registreren in `Duiklogboek.xlsx`.
- Overzicht bekijken + exporteren (gesorteerd op datum en duikplaats).
- Eenvoudige afrekening (vergoeding per duik).

## Starten (lokaal)
1. Maak een Python 3.10+ omgeving.
2. Installeer dependencies:  
   `pip install -r requirements.txt`
3. Start de app:  
   `streamlit run app.py`

## Deploy (Streamlit Cloud)
- Upload deze map als GitHub repo en koppel in Streamlit Cloud.
- Zet secrets/variabelen niet nodig in deze versie (alles is file-based).

> **Belangrijk**: Wijzig na de eerste login het admin-wachtwoord via de pagina **Beheer → Gebruikers**.
