#!/usr/bin/env python3
"""Script to send an embed to a discord channel with CTFTime scores"""

import datetime
import os

import pymongo
import pytz
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

client = pymongo.MongoClient(os.getenv("MONGODB_CONNECTION_URL"))
db = client.Corax  # ! Change this line to the correct collection name
collection = db.ctftime_history  # ! Change this to be the correct table name

TEAM_ID = "113107"

HEADERS = {"User-Agent": "Corax"}

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
PFP_URL = "https://cdn.discordapp.com/attachments/719605546101113012/731453497479790672/ctftime.png"


def scrape_website(team_id):
    """Downloads the website and scapes the rating"""
    page = requests.get(f"https://ctftime.org/team/{team_id}", headers=HEADERS)
    soup = BeautifulSoup(page.content, "html.parser")
    rating_div = soup.find(id="rating_2020")
    rating_a = str(rating_div.select('a[href="/stats/NO"]')[0])
    rating_a = rating_a.replace('<a href="/stats/NO">', "").replace("</a>", "")
    return int(rating_a)


def get_world_rating(team_id):
    """Parses the JSON and gets the data"""
    response = requests.get(
        f"https://ctftime.org/api/v1/teams/{team_id}/", headers=HEADERS)
    print(response)
    return int(response.json()["rating"][0]["2020"]["rating_place"])


def post_discord_message(data):
    """Posts to the discord webhook url"""
    requests.post(DISCORD_WEBHOOK_URL, json=data)


def main():
    """The main function that will be ran when the script runs"""
    last_entry = collection.find_one(sort=[("_id", pymongo.DESCENDING)])
    try:
        last_rating = {
            "world": int(last_entry["world"]),
            "region": int(last_entry["region"])
        }
    except TypeError:
        last_rating = {
            "world": "NO_DATA",
            "region": "NO_DATA"
        }

    position = get_world_rating(TEAM_ID)
    if last_rating["world"] == "NO_DATA":
        # Hvis vi mangler data
        change = ":x:"
    else:
        if position > last_rating["world"]:
            # Vi har falt
            change = ":arrow_down:"
        elif position < last_rating["world"]:
            # Vi har gått opp
            change = ":arrow_up:"
        else:
            # Ingen endring
            change = ":arrow_right:"

    position_regional = scrape_website(TEAM_ID)
    if last_rating["region"] == "NO_DATA":
        change_regional = ":x:"
    else:
        if position_regional > last_rating["region"]:
            change_regional = ":arrow_down:"
        elif position_regional < last_rating["region"]:
            change_regional = ":arrow_up:"
        else:
            change_regional = ":arrow_right:"

    time_now = pytz.timezone(
        "Europe/Oslo").localize(datetime.datetime.now().replace(microsecond=0)).isoformat()

    try:
        if last_entry["checked_at"] is None:
            last_checked = "NO_DATA"
        else:
            last_checked = last_entry["checked_at"]
    except TypeError:
        last_checked = "NO_DATA"

    post_discord_message({
        "username": "CTFTime",
        "avatar_url": DISCORD_WEBHOOK_URL,
        "embeds": [{
            "title": "CTFTime ranking update",
            "description": f"World: {change} {position}\nRegion: {change_regional} {position_regional}",
            "timestamp": time_now,
            "color": 11610890,
            "fields": [{
                "name": "Last checked",
                "value": last_checked,
                "inline": True
            }, {
                "name": "Last rating",
                "value": f"World: {last_rating['world']}\nRegion: {last_rating['region']}",
                "inline": True
            }]
        }]
    })

    collection.insert_one(
        {"checked_at": time_now, "region": position_regional, "world": position})


if __name__ == "__main__":
    main()
