import requests
from bs4 import BeautifulSoup
from rich import print
from rich.table import Table
import sys
import os
import xml.etree.ElementTree as ET
from rich.console import Console
from rich.progress import Progress
import threading
from queue import Queue
import argparse
from urllib.parse import urljoin
import logging



BASE_BBS_URL = "https://www.lexaloffle.com/"
console = Console()
q = Queue()


parser = argparse.ArgumentParser()
parser.add_argument("-t", type=int, default=20,
                    help="Set the number of parallel download threads.")
parser.add_argument("-p", type=int, default=10,
                    help="Set the number of pages.")
args = parser.parse_args()

print("""
░▒█▀▀█░▀█▀░▒█▀▀▄░▒█▀▀▀█░▄▀▀▄
░▒█▄▄█░▒█░░▒█░░░░▒█░░▒█░▄▀▀▄
░▒█░░░░▄█▄░▒█▄▄▀░▒█▄▄▄█░▀▄▄▀
░█▀▄░█▀▀▄░█▀▀▄░▀█▀░█░░▄▀▀▄░█▀▀▄░█▀▄░█▀▀░█▀▀▄
░█░░░█▄▄█░█▄▄▀░░█░░█░░█░░█░█▄▄█░█░█░█▀▀░█▄▄▀
░▀▀▀░▀░░▀░▀░▀▀░░▀░░▀▀░░▀▀░░▀░░▀░▀▀░░▀▀▀░▀░▀▀
                                                                                  
Developed by @icaroferre

""")

from urllib.parse import urljoin

class PICOGAME:
    def __init__(self, title, url):
        self.title = title
        self.url = url
        self.card_url = ""
        self.card_name = ""
        self.description = ""
        self.developer = ""
        self.thumb_url = ""
        self.thumb_file = ""

    def getDetails(self):
        # Correct URL construction using urljoin
        cardUrl = urljoin(BASE_BBS_URL, "/bbs/" + self.url)
        console.print(f"[yellow]Fetching card URL: {cardUrl}[/yellow]")
        cardPage = getPageContent(cardUrl)
        if cardPage is None:
            logging.error(f"Failed to fetch page content for {self.title}")
            return

        try:
            # Updated selector: Find 'a' tags with href ending with '.p8.png'
            a_tags = cardPage.find_all("a", href=True)
            for a in a_tags:
                href = a['href']
                if href.endswith('.p8.png'):
                    # Use urljoin to handle relative URLs
                    self.card_url = urljoin(BASE_BBS_URL, href)
                    self.card_name = os.path.basename(self.card_url)
                    break
            if not self.card_url:
                raise AttributeError("Cartridge file link not found.")

            console.print(f"[green]Cartridge file URL: {self.card_url}[/green]")

            # Extract developer
            devDiv = cardPage.find("div", {"style": "font-size:9pt; margin-bottom:4px"})
            self.developer = devDiv.text.strip() if devDiv else "Unknown"

            # Extract description
            descriptionDiv = cardPage.find("div", {"style": "min-height:44px;"})
            if descriptionDiv:
                description_text = descriptionDiv.get_text(separator="\n").strip()
                split_text = description_text.split("Copy and paste the snippet below into your HTML.")
                if len(split_text) > 1:
                    self.description = split_text[1].replace(
                        "Note: This cartridge's settings do not allow embedded playback. A [Play at lexaloffle] link will be included instead.", ""
                    ).replace("\t", "").replace("\r", "").strip()
                    while "\n\n" in self.description:
                        self.description = self.description.replace("\n\n", "\n")
                else:
                    self.description = description_text
            else:
                self.description = "No description available."

            # Extract thumbnail URL
            images = cardPage.find_all("img")
            self.thumb_url = ""
            for img in images:
                src = img.get("src", "")
                if "thumbs" in src:
                    self.thumb_url = urljoin(BASE_BBS_URL, src)
                    self.thumb_file = os.path.basename(self.thumb_url)
                    break

            if not self.thumb_url:
                self.thumb_url = ""
                self.thumb_file = ""

            self.download()

        except AttributeError as e:
            console.print(f"[red]Failed to find necessary details for {self.title}. Error: {e}[/red]")
            logging.error(f"Failed to parse details for {self.title}: {e}")

    def download(self):
        console.print(f"[cyan]Downloading game: {self.title}[/cyan]")
        if self.card_url:
            downloadFile(self.card_url, self.card_name, "output")
        else:
            console.print(f"[red]No cartridge URL found for {self.title}[/red]")
            logging.warning(f"No cartridge URL for {self.title}")

        if self.thumb_url:
            downloadFile(self.thumb_url, self.thumb_file, os.path.join("output", "media", "screenshots"))
        else:
            console.print(f"[yellow]No thumbnail URL found for {self.title}[/yellow]")
            logging.warning(f"No thumbnail URL for {self.title}")



def threader():
    while True:
        game = q.get()
        print(game)
        try:
            game.getDetails()
            print(game.getDetails())
        except:
            console.print("Failed to download: {}".format(game.title))
        q.task_done()


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; YourScriptName/1.0; +https://yourwebsite.com/)"
}
def downloadFile(url, filename, path):
    # Ensure the path does not start with '/' to prevent absolute path issues
    if path.startswith('/'):
        path = path[1:]
    full_path = os.path.join(sys.path[0], path, filename)
    try:
        response = requests.get(url, stream=True, headers=HEADERS)
        response.raise_for_status()  # Raises HTTPError for bad responses
        os.makedirs(os.path.dirname(full_path), exist_ok=True)  # Ensure directories exist
        with open(full_path, 'wb') as outfile:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    outfile.write(chunk)
        console.print(f"[green]Successfully downloaded {filename}[/green]")
        logging.info(f"Downloaded {filename} from {url}")
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Failed to download {filename} from {url}. Error: {e}[/red]")
        logging.error(f"Failed to download {filename} from {url}: {e}")
    except Exception as e:
        console.print(f"[red]Unexpected error while downloading {filename}: {e}[/red]")
        logging.error(f"Unexpected error for {filename}: {e}")


def createFolder(foldername):
    try:
        path = sys.path[0] + "/" + foldername
        os.mkdir(path, 0o777)
    except FileExistsError:
        pass

def getPageContent(url, params=None):
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()  # Raises HTTPError for bad responses
        content = BeautifulSoup(res.content, "html.parser")
        return content
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Error fetching {url}: {e}[/red]")
        return None


def getGamesFromPage(url, params):
    with console.status("[bold green]Scraping page for games...") as status:
        content = getPageContent(url, params)
        if content is None:
            return []
        links = content.find_all("a")
        games_found = []
        for i in links:
            link_url = i.get("href", "")
            link_title = i.text.strip()
            if "?tid" in link_url:
                new_game = PICOGAME(link_title, link_url)
                games_found.append(new_game)
    console.print(f"Games found: {len(games_found)}")
    return games_found



def printGames(games):
    table = Table(title="Games found")
    table.add_column("Title", justify="left", no_wrap=True)
    table.add_column("Developer", style="magenta")
    table.add_column("Card URL", style="green")
    table.add_column("Thumbnail", justify="right", style="green")
    for i in games:
        table.add_row(i.title, i.developer, i.card_url, i.thumbnail)
    console.print(table)

def createInitialFolder():
    createFolder("output")
    createFolder("output/media")
    createFolder("output/media/screenshots")

def generateXMLFile(games):
    with console.status("[bold green]Generating XML file...") as status:
        data = ET.Element('gameList')
        for i in games:
            newgame = ET.SubElement(data, 'game')
            name = ET.SubElement(newgame, 'name')
            path = ET.SubElement(newgame, 'path')
            image = ET.SubElement(newgame, 'image')
            developer = ET.SubElement(newgame, 'developer')
            description = ET.SubElement(newgame, 'desc')
            name.text = i.title
            path.text = "./" + i.card_name
            developer.text = i.developer
            description.text = i.description
            image.text = "./media/screenshots/" + i.thumb_file
        
        mydata = ET.tostring(data).decode("utf-8")
        myfile = open(sys.path[0] + "/output/gamelist.xml", "w")
        myfile.write(str(mydata))
        print("XML file written successfully.")

def searchAndDownload():
    games = []
    for i in range(args.p):
        params = {
            "cat": 7,
            "sub": 2,
            "mode": "carts",
            "orderby": "featured",
            "page": i + 1
        }
        url = "https://www.lexaloffle.com/bbs/"
        newgames = getGamesFromPage(url, params)
        for n in newgames:
            games.append(n)
            
    with console.status(f"[bold green]Downloading {len(games)} games ({args.t} threads)...") as status:
        for i in games:
            q.put(i)
        q.join()
    return games


for x in range(args.t):
    t = threading.Thread(target=threader)
    t.daemon = True
    t.start()

if __name__ == '__main__':

    createInitialFolder()
    games = searchAndDownload()
    generateXMLFile(games)


