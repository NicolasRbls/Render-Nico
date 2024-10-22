import os
import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
from pymongo import MongoClient
import re
from collections import Counter

# Connexion à MongoDB
mongodb_uri = os.getenv('MONGODB_URI')

if mongodb_uri is None:
    print("Erreur : URI MongoDB non défini dans les variables d'environnement.")
    exit(1)

# Connexion à MongoDB
client = MongoClient(mongodb_uri)
db = client['crawler_db']
collection = db['crawled_urls']

# Test de connexion à MongoDB
try:
    client.admin.command('ping')
    print("Connexion à MongoDB réussie")
except Exception as e:
    print(f"Erreur de connexion à MongoDB : {e}")
    exit(1)

# Fonction pour récupérer des URLs dynamiques en fonction du thème
def get_dynamic_urls(theme):
    search_url = f"https://www.bing.com/news/search?q={urllib.parse.quote(theme)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    links = set()
    for a_tag in soup.find_all('a', href=True):
        link = a_tag['href']
        if 'http' in link:
            links.add(link)
    
    return links

# Fonction pour vérifier si une URL a déjà été explorée
def is_url_explored(url):
    return collection.find_one({"url": url}) is not None

# Fonction pour enregistrer les résultats
def save_to_database(url, num_links, word_dict):
    if is_url_explored(url):
        print(f"L'URL {url} a déjà été explorée. Ignorée.")
        return

    data = {
        "url": url,
        "num_links": num_links,
        "word_frequencies": word_dict
    }
    try:
        collection.insert_one(data)
        print(f"Résultats insérés dans MongoDB pour {url}")
        print(f"Données insérées : {data}")
    except Exception as e:
        print(f"Erreur lors de l'insertion dans MongoDB : {e}")

# Fonction pour extraire les liens spécifiques et traiter le contenu
def get_specific_links(url, theme, headers):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        links = set()

        # Recherche du thème dans le texte de la page
        page_text = soup.get_text(separator=' ')
        if theme.lower() in page_text.lower():
            print(f"Thème '{theme}' trouvé dans {url}")
            words = clean_text(page_text)

            # Compter les 10 mots les plus fréquents
            word_counts = Counter(words).most_common(10)
            word_dict = dict(word_counts)

            # Enregistrer dans la base de données
            save_to_database(url, len(links), word_dict)

        # Ajouter des liens trouvés dans la page
        for a_tag in soup.find_all('a', href=True):
            link = a_tag['href']
            full_link = urllib.parse.urljoin(url, link)
            links.add(full_link)

        return links

    except requests.RequestException as e:
        print(f"Erreur lors de la récupération de la page {url}: {e}")
        return set()  # Retourne un ensemble vide si l'URL est inaccessible

# Nettoyage du texte
def clean_text(text):
    text = re.sub(r'\W+', ' ', text)
    words = text.lower().split()
    words = [word for word in words if len(word) > 3 and not word.isdigit()]
    return words

# Fonction principale pour explorer un thème
def crawl_with_theme(theme, depth):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }

    # Obtenir des URLs dynamiques
    to_crawl = get_dynamic_urls(theme)
    crawled = set()
    depth_count = 0

    while to_crawl and depth_count < depth:
        url = to_crawl.pop()
        if url not in crawled:
            try:
                print(f"Exploring: {url}")
                links = get_specific_links(url, theme, headers)
                to_crawl.update(links - crawled)
                crawled.add(url)
                time.sleep(1)

            except Exception as e:
                print(f"Erreur lors de l'exploration de l'URL {url}: {e}")
                continue  # Continue même si une erreur se produit

        depth_count += 1

    print(f"Exploration terminée : {len(crawled)} pages explorées.")

# Exécuter le crawler avec un thème et une profondeur
theme = "football"
crawl_with_theme(theme, depth=30)
