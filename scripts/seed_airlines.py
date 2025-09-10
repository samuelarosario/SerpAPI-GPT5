"""
Seed the airlines table with a curated list of common airlines and IATA codes.
- Uses INSERT OR IGNORE (idempotent)
- Leaves existing curated names/logos intact
"""
from __future__ import annotations

import os
import sys

# Ensure repository root is on sys.path so `Main` package imports resolve
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from Main.core.db_utils import open_connection

AIRLINES: list[tuple[str,str]] = [
    # North America
    ("AA","American Airlines"),
    ("UA","United Airlines"),
    ("DL","Delta Air Lines"),
    ("WN","Southwest Airlines"),
    ("AS","Alaska Airlines"),
    ("B6","JetBlue Airways"),
    ("NK","Spirit Airlines"),
    ("F9","Frontier Airlines"),
    ("G4","Allegiant Air"),
    ("AC","Air Canada"),
    ("WS","WestJet"),
    ("PD","Porter Airlines"),
    ("AM","Aeroméxico"),
    ("Y4","Volaris"),
    ("VB","Viva Aerobus"),
    ("CM","Copa Airlines"),
    # Latin America
    ("LA","LATAM Airlines"),
    ("AV","Avianca"),
    ("AR","Aerolíneas Argentinas"),
    ("G3","GOL Linhas Aéreas"),
    ("AD","Azul Linhas Aéreas"),
    ("H2","Sky Airline"),
    # Europe
    ("BA","British Airways"),
    ("EI","Aer Lingus"),
    ("U2","easyJet"),
    ("FR","Ryanair"),
    ("W6","Wizz Air"),
    ("LH","Lufthansa"),
    ("LX","Swiss"),
    ("OS","Austrian Airlines"),
    ("SN","Brussels Airlines"),
    ("KL","KLM"),
    ("AF","Air France"),
    ("AZ","ITA Airways"),
    ("IB","Iberia"),
    ("VY","Vueling"),
    ("UX","Air Europa"),
    ("TP","TAP Air Portugal"),
    ("SK","SAS Scandinavian Airlines"),
    ("AY","Finnair"),
    ("LO","LOT Polish Airlines"),
    ("OK","Czech Airlines"),
    ("TK","Turkish Airlines"),
    ("PC","Pegasus Airlines"),
    ("DY","Norwegian Air Shuttle"),
    ("BT","airBaltic"),
    ("RO","TAROM"),
    ("A3","Aegean Airlines"),
    ("FI","Icelandair"),
    # Middle East & North Africa
    ("EK","Emirates"),
    ("EY","Etihad Airways"),
    ("QR","Qatar Airways"),
    ("SV","Saudia"),
    ("WY","Oman Air"),
    ("GF","Gulf Air"),
    ("KU","Kuwait Airways"),
    ("RJ","Royal Jordanian"),
    ("ME","Middle East Airlines"),
    ("MS","EgyptAir"),
    ("AT","Royal Air Maroc"),
    # Africa (Sub‑Saharan)
    ("ET","Ethiopian Airlines"),
    ("KQ","Kenya Airways"),
    ("SA","South African Airways"),
    ("4Z","Airlink"),
    ("WB","RwandAir"),
    ("DT","TAAG Angola Airlines"),
    ("KP","ASKY Airlines"),
    # Asia
    ("NH","All Nippon Airways"),
    ("JL","Japan Airlines"),
    ("KE","Korean Air"),
    ("OZ","Asiana Airlines"),
    ("CX","Cathay Pacific"),
    ("HX","Hong Kong Airlines"),
    ("CA","Air China"),
    ("MU","China Eastern Airlines"),
    ("CZ","China Southern Airlines"),
    ("HU","Hainan Airlines"),
    ("CI","China Airlines"),
    ("BR","EVA Air"),
    ("SQ","Singapore Airlines"),
    ("TR","Scoot"),
    ("MH","Malaysia Airlines"),
    ("OD","Batik Air Malaysia"),
    ("GA","Garuda Indonesia"),
    ("QG","Citilink"),
    ("VN","Vietnam Airlines"),
    ("VJ","VietJet Air"),
    ("TG","Thai Airways"),
    ("FD","Thai AirAsia"),
    ("PR","Philippine Airlines"),
    ("5J","Cebu Pacific"),
    ("AI","Air India"),
    ("UK","Vistara"),
    ("6E","IndiGo"),
    ("SG","SpiceJet"),
    ("UL","SriLankan Airlines"),
    ("PK","Pakistan International Airlines"),
    # Oceania
    ("QF","Qantas"),
    ("JQ","Jetstar"),
    ("VA","Virgin Australia"),
    ("NZ","Air New Zealand"),
    ("PX","Air Niugini"),
    ("FJ","Fiji Airways"),
    # Sentinel/unknown
    ("ZZ","Unknown Carrier"),
]

def main(db_path: str | None = None) -> None:
    # Resolve database path to an absolute path rooted at the repository root
    if not db_path:
        db_path = os.path.join(REPO_ROOT, 'DB', 'Main_DB.db')
    inserted = 0
    attempted = len(AIRLINES)
    with open_connection(db_path) as conn:
        cur = conn.cursor()
        for code, name in AIRLINES:
            try:
                cur.execute(
                    "INSERT OR IGNORE INTO airlines(airline_code, airline_name) VALUES (?, ?)",
                    (code, name)
                )
                if cur.rowcount == 1:
                    inserted += 1
            except Exception as e:
                print(f"Error inserting {code}: {e}")
        conn.commit()
    print(f"Airlines seeded: attempted={attempted} inserted={inserted} ignored={attempted - inserted}")

if __name__ == "__main__":
    main()
