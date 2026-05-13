import requests
from bs4 import BeautifulSoup
import os

# Tähän koodisi, joka hakee Medipoliksen, Apilan ja Kaupunginsairaalan listat

html_sisalto = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body>
    <h1>Päivän ruokalistat</h1>
    <!-- Tähän parsittu data taulukoina tai listoina -->
</body>
</html>
"""

os.makedirs("public", exist_ok=True)
with open("public/index.html", "w", encoding="utf-8") as f:
    f.write(html_sisalto)
