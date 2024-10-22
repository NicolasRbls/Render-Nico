import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
from pymongo import MongoClient
import re
from collections import Counter
import json

# Connexion à MongoDB (utilise ton URI)
client = MongoClient("mongodb+srv://nicolas:cc5sYdkPWGpV81ep@cluster0.qx6hg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

# Accéder à la base de données et à la collection
db = client['crawler_db']  # Nom de ta base de données
collection = db['crawled_urls']  # Nom de la collection

# Thème à explorer
def crawl_with_theme(theme, start_url, depth):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }

    def get_specific_links(url):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            links = set()

            # Recherche du thème dans le texte de la page
            page_text = soup.get_text(separator=' ')
            if theme.lower() in page_text.lower():  # Si le thème est trouvé sur la page
                print(f"Thème '{theme}' trouvé dans {url}")
                words = clean_text(page_text)

                # Compter les 10 mots les plus fréquents
                word_counts = Counter(words).most_common(10)
                word_dict = dict(word_counts)

                # Enregistrer dans la base de données
                save_to_database(url, len(links), word_dict)

            # Ajouter **tous les liens** à explorer, pas seulement ceux qui contiennent le thème
            for a_tag in soup.find_all('a', href=True):
                link = a_tag['href']
                full_link = urllib.parse.urljoin(url, link)
                links.add(full_link)  # Ajouter tous les liens

            return links

        except requests.RequestException as e:
            print(f"Erreur lors de la récupération de la page {url}: {e}")
            return set()


    # Fonction pour enregistrer les résultats dans MongoDB
    def save_to_database(url, num_links, word_dict):
        data = {
            "url": url,
            "num_links": num_links,
            "word_frequencies": word_dict
        }
        try:
            # Insérer le document dans MongoDB
            collection.insert_one(data)
            print(f"Résultats insérés dans MongoDB pour {url}")
        except Exception as e:
            print(f"Erreur lors de l'insertion dans MongoDB : {e}")

    # Nettoyer le texte
    def clean_text(text):
        text = re.sub(r'\W+', ' ', text)
        words = text.lower().split()
        words = [word for word in words if len(word) > 3 and not word.isdigit()]
        return words

    to_crawl = {start_url}
    crawled = set()

    depth_count = 0
    while to_crawl and depth_count < depth:
        url = to_crawl.pop()
        if url not in crawled:
            print(f"Exploring: {url}")
            links = get_specific_links(url)
            to_crawl.update(links - crawled)
            crawled.add(url)
            time.sleep(1)
        depth_count += 1

    print(f"Exploration terminée : {len(crawled)} pages explorées.")

# Exemple d'exécution avec un thème
theme = "football"  # Le thème peut être passé en paramètre
start_url = "https://www.lequipe.fr/"
crawl_with_theme(theme, start_url, depth=1)
