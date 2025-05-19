import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import csv
import os
import re

class WebCrawler:
    def __init__(self, url_file="urls.txt", max_depth=3, delay=1.0, output_file="crawl_results.csv"):
        self.url_file = url_file
        self.max_depth = max_depth
        self.delay = delay
        self.output_file = output_file
        self.visited = set()
        self.results = []
        # Expressions régulières pour extraire les données
        self.akia_pattern = re.compile(r'AKIA[A-Z0-9]{16}')
        self.secret_key_pattern = re.compile(r'[A-Za-z0-9/+=]{40}')
        self.region_pattern = re.compile(r'(us|eu|ap|sa|ca|me|af|cn)-[a-z]+-\d')
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

    def read_urls(self):
        """Lire les URLs à partir du fichier texte."""
        if not os.path.exists(self.url_file):
            raise FileNotFoundError(f"Le fichier {self.url_file} n'existe pas.")
        with open(self.url_file, 'r', encoding='utf-8') as file:
            urls = [line.strip() for line in file if line.strip() and not line.startswith('#')]
        return urls

    def is_valid_url(self, url):
        """Vérifier si une URL est valide."""
        try:
            result = requests.head(url, allow_redirects=True, timeout=5)
            return result.status_code == 200
        except requests.RequestException:
            return False

    def save_results(self):
        """Sauvegarder les résultats dans un fichier CSV."""
        with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['url', 'title', 'depth', 'source_url', 'akia_key', 'secret_key', 'region', 'email']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for result in self.results:
                writer.writerow(result)

    def extract_data(self, text):
        """Extraire les clés AKIA, SECRET KEY, REGION et EMAIL du texte."""
        akia_keys = self.akia_pattern.findall(text) or []
        secret_keys = self.secret_key_pattern.findall(text) or []
        regions = self.region_pattern.findall(text) or []
        emails = self.email_pattern.findall(text) or []
        return {
            'akia_key': ';'.join(akia_keys) if akia_keys else '',
            'secret_key': ';'.join(secret_keys) if secret_keys else '',
            'region': ';'.join(regions) if regions else '',
            'email': ';'.join(emails) if emails else ''
        }

    def crawl(self, url, source_url, depth=0):
        """Explorer une URL à une profondeur donnée."""
        if depth > self.max_depth or url in self.visited:
            return

        print(f"Crawling: {url} (Depth: {depth})")
        self.visited.add(url)

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()

            # Extraire les données
            extracted_data = self.extract_data(page_text)

            # Stocker les informations de la page
            page_info = {
                'url': url,
                'title': soup.title.string.strip() if soup.title else 'No title',
                'depth': depth,
                'source_url': source_url,
                'akia_key': extracted_data['akia_key'],
                'secret_key': extracted_data['secret_key'],
                'region': extracted_data['region'],
                'email': extracted_data['email']
            }
            self.results.append(page_info)

            # Trouver tous les liens
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)
                
                # Vérifier que l'URL appartient au même domaine
                if urlparse(absolute_url).netloc == urlparse(source_url).netloc:
                    if self.is_valid_url(absolute_url):
                        time.sleep(self.delay)  # Respecter le site
                        self.crawl(absolute_url, source_url, depth + 1)

        except requests.RequestException as e:
            print(f"Error crawling {url}: {e}")

    def run(self):
        """Exécuter le crawler pour toutes les URLs du fichier."""
        urls = self.read_urls()
        if not urls:
            print("Aucune URL valide trouvée dans le fichier.")
            return

        for url in urls:
            if self.is_valid_url(url):
                print(f"Démarrage du crawl pour {url}")
                self.crawl(url, url, depth=0)
            else:
                print(f"URL invalide ou inaccessible : {url}")

        # Sauvegarder les résultats
        if self.results:
            self.save_results()
            print(f"Résultats sauvegardés dans {self.output_file}")
        else:
            print("Aucun résultat à sauvegarder.")

        return self.results

# Exemple d'utilisation
if __name__ == "__main__":
    crawler = WebCrawler(
        url_file="urls.txt",
        max_depth=3,
        delay=1.0,
        output_file="crawl_results.csv"
    )
    results = crawler.run()