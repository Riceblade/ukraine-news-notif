import requests
import json
import time
import traceback
import random
import os

from datetime import datetime, timedelta
from colorama import Fore, Style
from bs4 import BeautifulSoup


def traceback_maker(err):
    _traceback = ''.join(traceback.format_tb(err.__traceback__))
    error = ('{1}{0}: {2}').format(type(err).__name__, _traceback, err)
    return error


class Feed:
    def __init__(self, html_data):
        self.html = html_data
        self.info = html_data.find("div", {"class": "title"}).text
        self.id = html_data.attrs.get("data-id", None)
        self.extra = html_data.find("a", {"data-id": self.id, "class": "comment-link"}).attrs.get("href", None)

    @property
    def video(self):
        main_video = self.html.attrs.get("data-twitpic", None)
        if main_video and "video" in main_video:
            return main_video

        find_video = self.html.find("blockquote", {"class": "twitter-video"})
        if not find_video:
            return None
        return find_video.find("a").attrs.get("href", None)

    @property
    def image(self):
        find_img = self.html.find("div", {"class": "img"})
        if not find_img:
            return None
        try:
            return find_img.find("img").attrs.get("src", None)
        except AttributeError:
            return None


class Article:
    def __init__(self, feed: Feed, html_data):
        self.html = html_data
        self.feed = feed

        self.image = feed.image
        self.info = feed.info
        self.id = feed.id
        self.extra = feed.extra
        self.video = feed.video

    @property
    def source(self):
        html = self.html.find("a", {"class": "source-link"})
        if not html:
            return None
        return html.attrs.get("href", None)


def read_json(key: str = None, default=None):
    with open("./config.json", "r") as f:
        data = json.load(f)
    if key:
        return data.get(key, default)
    return data


def write_json(**kwargs):
    data = read_json()
    for key, value in kwargs.items():
        data[key] = value
    with open("./config.json", "w") as f:
        json.dump(data, f, indent=2)


def webhook(html_content: Article):
    os.system("""
              osascript -e 'display notification "{}" with title "{}"'
              """.format(html_content.info, "New Ukraine news"))

def pretty_print(symbol: str, text: str):
    data = {
        "+": Fore.GREEN, "-": Fore.RED,
        "!": Fore.YELLOW, "?": Fore.CYAN,
    }

    colour = data.get(symbol, Fore.WHITE)
    print(f"{colour}[{symbol}]{Style.RESET_ALL} {text}")


def fetch(url: str):
    r = requests.get(
        url, headers={
            "User-Agent": read_json("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"),
            "Content-Type": "text/html; charset=UTF-8",
        }
    )
    text = r.content.decode("utf-8")
    return text


def main():
    while True:
        try:
            check_in_rand = random.randint(45, 75)

            pretty_print("?", f"{datetime.now()} - Checking for new articles")
            pretty_print("+", "Fetching all articles and parsing HTML...")

            r = fetch("https://liveuamap.com/")
            html = BeautifulSoup(r, "html.parser")

            try:
                feeder = html.find("div", {"id": "feedler"})
                latest_news = next((g for g in feeder), None)
            except TypeError:
                pretty_print("!", "Failed to get feeder, probably 500 error, trying again...")
                time.sleep(5)
                continue

            news = Feed(latest_news)
            if news.id != read_json("last_id", None):
                pretty_print("+", "New article found, checking article...")
                r_extra = fetch(news.extra)
                extra_html = BeautifulSoup(r_extra, "html.parser")
                webhook(Article(news, extra_html))
                write_json(last_id=news.id)
                pretty_print("!", news.info)
            else:
                pretty_print("-", f"Found no news... waiting {check_in_rand} seconds")
        except Exception as e:
            pretty_print("!", traceback_maker(e))

        time.sleep(check_in_rand)


try:
    main()
except KeyboardInterrupt:
    pretty_print("!", "Exiting...")
