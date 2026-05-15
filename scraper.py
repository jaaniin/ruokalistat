import requests
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime, timedelta

def hae_kanresta():
    try:
        url = "https://kanresta.fi/ravintolat/oulun-kaupunginsairaala/"
        vastaus = requests.get(url, timeout=10)
        soup = BeautifulSoup(vastaus.content, "html.parser")
        viikonpaiva = datetime.today().weekday()
        
        if viikonpaiva > 4: return "Viikonloppu – Suljettu"
        
        aktiivinen_viikko = soup.find("div", class_="tab-pane active")
        if not aktiivinen_viikko: return "Ei listaa saatavilla"
        
        paivat = aktiivinen_viikko.find_all("div", class_="weekday-block")
        if viikonpaiva < len(paivat):
            tanaan = paivat[viikonpaiva]
            tulos = []
            ruoat = tanaan.find_all("div", class_="weekday-panel")
            for r in ruoat:
                annos_elem = r.find("div", class_="portions")
                if annos_elem:
                    if annos_elem.find("div", class_="price-block"):
                        annos_elem.find("div", class_="price-block").decompose()
                    teksti = " ".join(annos_elem.text.split())
                    lisa_elem = r.find("div", class_="lunch-add-text")
                    lisa = f" ({' '.join(lisa_elem.text.split())})" if lisa_elem and lisa_elem.text.strip() else ""
                    if teksti: tulos.append(f"<li>{teksti}{lisa}</li>")
            return "<ul>" + "".join(tulos) + "</ul>"
    except: return "Virhe haussa"

def hae_medipolis():
    try:
        cost_center = "3508"
        url = f"https://www.compass-group.fi/menuapi/feed/json?costNumber={cost_center}&language=fi"
        headers = {"User-Agent": "Mozilla/5.0"}
        data = requests.get(url, headers=headers, timeout=10).json()
        tanaan_str = datetime.now().strftime("%Y-%m-%d")
        
        for paiva in data.get("MenusForDays", []):
            if paiva.get("Date", "").startswith(tanaan_str):
                tulos = []
                for menu in paiva.get("SetMenus", []):
                    for ruoka_string in menu.get("Components", []):
                        annokset = re.findall(r'([^()]+(?:[(][^()]*[)])?)', ruoka_string)
                        for a in annokset:
                            if a.strip() and "None" not in a:
                                tulos.append(f"<li>{a.strip()}</li>")
                return "<ul>" + "".join(tulos) + "</ul>"
        return "Ei listaa tälle päivälle"
    except: return "Virhe haussa"

def hae_apila():
    try:
        url = "https://aromimenu.cgisaas.fi/PPSHPAromieMenus/FI/Default/PPSHP/Apila/Restaurant.aspx"
        vastaus = requests.get(url, timeout=10)
        soup = BeautifulSoup(vastaus.content, "html.parser")
        # Haetaan vain ensimmäinen päiväpaneeli (Tänään)
        paneeli = soup.find("div", class_="DayDataPanel")
        if not paneeli: return "Ei listaa saatavilla"
        
        tulos = []
        ateriarivit = paneeli.find_all("div", class_="emenu_tab_panel_row")
        for rivi in ateriarivit:
            nimi = rivi.find("span", id=lambda x: x and "MenuName" in x)
            ruoat = rivi.find_all("span", id=lambda x: x and "SecureLabelDish" in x)
            dietti = rivi.find_all("span", id=lambda x: x and "SecureLabelDiets" in x)
            
            ruokalista = []
            for r, d in zip(ruoat, dietti):
                if r.text.strip():
                    ruokalista.append(f"{r.text.strip()} ({d.text.strip()})")
            
            if ruokalista:
                tulos.append(f"<li><strong>{nimi.text.strip()}:</strong> {', '.join(ruokalista)}</li>")
        return "<ul>" + "".join(tulos) + "</ul>"
    except: return "Virhe haussa"

# Generoidaan lopullinen HTML
pvm = datetime.now().strftime("%d.%m.%Y")
paivitysaika = (datetime.utcnow() + timedelta(hours=3)).strftime("%d.%m.%Y klo %H:%M")

html = f"""
<!DOCTYPE html>
<html lang="fi">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Päivän Ruokalistat</title>
    <style>
        body {{ font-family: sans-serif; line-height: 1.4; padding: 20px; background: #f4f4f4; }}
        .card {{ background: white; padding: 15px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        h2 {{ color: #0056b3; border-bottom: 2px solid #eee; padding-bottom: 5px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 5px; }}
        .footer {{ text-align: center; color: #666; font-size: 0.9em; margin-top: 30px; }}
    </style>
</head>
<body>
    <h1>Lounaslistat {pvm}</h1>
    <div class="card"><h2>Ravintola Apila</h2>{hae_apila()}</div>
    <div class="card"><h2>Medipolis</h2>{hae_medipolis()}</div>
    <div class="card"><h2>Kaupunginsairaala</h2>{hae_kanresta()}</div>
    <div class="footer">Tiedot päivitetty: {paivitysaika}</div>
</body>
</html>
"""

os.makedirs("public", exist_ok=True)
with open("public/index.html", "w", encoding="utf-8") as f:
    f.write(html)
