import requests
from bs4 import BeautifulSoup
import re
import os
import sys
from datetime import datetime, timedelta

pvm = datetime.now().strftime("%d.%m.%Y")

# Tarkistetaan onko sivusto jo päivitetty tänään
try:
    live_sivu = requests.get("https://jaaniin.github.io/ruokalistat/", timeout=10)
    if f"Lounaslistat {pvm}" in live_sivu.text:
        print("Tiedot on jo haettu tänään. Ei haeta uudestaan.")
        os.makedirs("public", exist_ok=True)
        with open("public/index.html", "w", encoding="utf-8") as f:
            f.write(live_sivu.text)
        sys.exit(0)
except:
    pass

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

AROMI_RESTAURANTS = {
    "Apila": "2502db2e-45f6-4eb1-9db4-737530dafa00",
    "Kielo": "4b9d6f01-6a36-4c0c-9261-4285ab9e9b4d",
}

def hae_aromi_menu(restaurant_name, restaurant_id=None):
    try:
        if not restaurant_id:
            restaurant_id = AROMI_RESTAURANTS.get(restaurant_name)

        if not restaurant_id:
            info_url = "https://aromimenu.cgisaas.fi/PPSHPAromieMenus/FI/Default/PPSHP/_/api/Common/Page/GetPageInfo"
            res = requests.get(info_url, headers={"Accept": "application/json"}, timeout=10)
            for r in res.json().get("Restaurants", []):
                if r.get("UniqueCode", "").lower() == restaurant_name.lower():
                    restaurant_id = r.get("Id")
                    break

        if not restaurant_id:
            return "Ravintolan tunnistetta ei löytynyt"

        tanaan = datetime.now().strftime("%Y-%m-%d")
        headers = {"Accept": "application/json"}

        # 1. Haetaan ruokailijaryhmät (Diner groups)
        dg_url = f"https://aromimenu.cgisaas.fi/PPSHPAromieMenus/FI/Default/PPSHP/{restaurant_name}/api/GetRestaurantPublicDinerGroups?id={restaurant_id}&startDate={tanaan}&endDate={tanaan}"
        dg_res = requests.get(dg_url, headers=headers, timeout=10)
        dg_data = dg_res.json()

        if not dg_data:
            return "Ei listaa tälle päivälle"

        diner_group = dg_data[0]
        diner_group["SuitabilityDietIds"] = []

        # 2. Haetaan päivän ateriat
        meals_url = f"https://aromimenu.cgisaas.fi/PPSHPAromieMenus/FI/Default/PPSHP/{restaurant_name}/api/Common/Restaurant/RestaurantMeals?Id={restaurant_id}&StartDate={tanaan}&EndDate={tanaan}"
        meals_res = requests.post(meals_url, json=diner_group, headers=headers, timeout=10)
        meals_data = meals_res.json()

        if not meals_data:
            return "Ei listaa tälle päivälle"

        tulos = []
        for day in meals_data:
            for meal in day.get("Meals", []):
                nimi = meal.get("MealName", "").strip()
                ruokalista = []
                for dish in meal.get("Dishes", []):
                    dish_name = dish.get("DishName", "").strip()
                    dietti = dish.get("DietDetails", "").strip()
                    if dish_name:
                        if dietti:
                            ruokalista.append(f"{dish_name} ({dietti})")
                        else:
                            ruokalista.append(dish_name)

                if ruokalista and nimi:
                    tulos.append(f"<li><strong>{nimi}:</strong> {', '.join(ruokalista)}</li>")

        if tulos:
            return "<ul>" + "".join(tulos) + "</ul>"
        return "Ei listaa tälle päivälle"
    except Exception as e:
        print(f"hae_{restaurant_name.lower()}() virhe: {e}")
        return "Virhe haussa"


def hae_apila():
    return hae_aromi_menu("Apila", AROMI_RESTAURANTS.get("Apila"))


def hae_kielo():
    return hae_aromi_menu("Kielo", AROMI_RESTAURANTS.get("Kielo"))

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
        h2 {{ color: #0056b3; border-bottom: 2px solid #eee; padding-bottom: 5px; margin-top: 0; }}
        h2 a {{ color: inherit; text-decoration: none; }}
        h2 a:hover {{ text-decoration: underline; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 5px; }}
        .footer {{ text-align: center; color: #666; font-size: 0.9em; margin-top: 30px; }}
    </style>
</head>
<body>
    <h1>Lounaslistat {pvm}</h1>
    <div class="card">
        <h2><a href="https://kanresta.fi/ravintolat/oulun-kaupunginsairaala/" target="_blank" rel="noopener noreferrer">Kaupunginsairaala</a></h2>
        {hae_kanresta()}
    </div>
    <div class="card">
        <h2><a href="https://aromimenu.cgisaas.fi/PPSHPAromieMenus/FI/Default/PPSHP/Kielo/Page/Restaurant" target="_blank" rel="noopener noreferrer">Ravintola Kielo</a></h2>
        {hae_kielo()}
    </div>
    <div class="card">
        <h2><a href="https://aromimenu.cgisaas.fi/PPSHPAromieMenus/FI/Default/PPSHP/Apila/Page/Restaurant" target="_blank" rel="noopener noreferrer">Ravintola Apila</a></h2>
        {hae_apila()}
    </div>
    <div class="card">
        <h2><a href="https://www.compass-group.fi/ravintolat-ja-ruokalistat/foodco/kaupungit/oulu/medipolismedusa/" target="_blank" rel="noopener noreferrer">Medipolis</a></h2>
        {hae_medipolis()}
    </div>
    <div class="footer">Tiedot päivitetty: {paivitysaika}</div>
</body>
</html>
"""

os.makedirs("public", exist_ok=True)
with open("public/index.html", "w", encoding="utf-8") as f:
    f.write(html)
