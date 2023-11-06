from src.Val import valApiAccess
import json
import threading
import os
import pandas as pd
import datetime
import logging

LOCK = threading.Lock()
DATA = []

def count_headshots(val, valRound):

    headshots = 0
    notHeadshots = 0

    for stats in valRound.get("playerStats"):
        if stats.get("subject") == val.PUUID:
            for shots in stats.get("damage"):
                headshots += shots.get("headshots")
                notHeadshots += shots.get("legshots") + shots.get("bodyshots")

    return headshots, notHeadshots

def get_mvp(val, valMatch):

    scores = {(player.get("stats").get("score")//player.get("stats").get("roundsPlayed")) : player.get("subject") for player in valMatch.get("players")}

    return ("YES" if val.PUUID == scores.get(max(scores.keys())) else "NO")

def get_kast(val, valMatch):

    kast = 0
    team = [player.get("teamId") for player in valMatch.get("players") if player.get("subject") == val.PUUID][0]

    for valRound in valMatch.get("roundResults"): 
        roundKast = 0
        death = 0

        for stats in valRound.get("playerStats"):
            if roundKast:
                break
            for kill in stats.get("kills"):
                
                # Check for kills
                if kill.get("killer") == val.PUUID:
                    roundKast = 1
                    break
                # Check for assists
                elif len(kill.get("assistants")) > 0 and val.PUUID in kill.get("assistants"):
                    roundKast = 1
                    # print("assist")
                    break
                # Check for survives or trades 
                elif kill.get("victim") == val.PUUID:

                    deathTime = kill.get("gameTime")

                    # implement better search
                    killIndex = [index for index in range(len(valMatch.get("kills")) - 1) if valMatch.get("kills")[index].get("gameTime") == deathTime][0]

                    nextKill = valMatch.get("kills")[killIndex + 1]

                    condition_1 = (nextKill.get("gameTime") - deathTime) <= 5000

                    nextKillTeam = [player.get("teamId") for player in valMatch.get("players") if player.get("subject") == nextKill.get("victim")][0] 

                    condition_2 = team != nextKillTeam

                    if condition_2 and condition_1:
                        roundKast = 1

                    death = 1
                    break

        if roundKast or not death:
            kast += 1 

    return int(round(kast/len(valMatch.get("roundResults")) * 100, 0))
        
def get_match_stats(val, valMatchId):

    logging.info("Thread %s : getting valorant match details", threading.current_thread().name)
    valMatch = val.get_match_details(valMatchId)

    logging.info("Thread %s : getting valorant maps information", threading.current_thread().name)
    maps = val.maps

    logging.info("Thread %s : getting valorant characters information", threading.current_thread().name)
    characters = val.characters

    logging.info("Thread %s : getting valorant ranks information", threading.current_thread().name)
    ranks = val.ranks

    logging.info("Thread %s : getting valorant seasons information", threading.current_thread().name)
    seasons = val.seasons


    for player in valMatch.get("players"):
        if(player.get("subject") == val.PUUID):
            logging.info("Thread %s : getting player stats", threading.current_thread().name)
            stats = player.get("stats") 

            logging.info("Thread %s : getting player character", threading.current_thread().name)
            character = characters.get(player.get("characterId"))

            logging.info("Thread %s : getting player team", threading.current_thread().name)
            team = player.get("teamId")

            logging.info("Thread %s : getting player rank", threading.current_thread().name)
            rank = ranks.get(player.get("competitiveTier")).get("tierName")

    logging.info("Thread %s : calculating player headshot percentage", threading.current_thread().name)
    sumHeadshots, sumNotHeadshots = [0,0]
    for valRound in valMatch.get("roundResults"):
        headshots, notHeadshots = count_headshots(val, valRound)
        sumHeadshots += headshots
        sumNotHeadshots += notHeadshots
    headshotPercentage = int(round(sumHeadshots/(sumHeadshots + sumNotHeadshots)*100, 0))

    logging.info("Thread %s : calculating player KAST percentage", threading.current_thread().name)
    kastPercentage = get_kast(val, valMatch)

    logging.info("Thread %s : getting match map", threading.current_thread().name)
    matchMap = maps.get(valMatch.get("matchInfo").get("mapId"))

    logging.info("Thread %s : getting match result", threading.current_thread().name)
    win = [t.get("won") for t in valMatch.get("teams") if t.get("teamId") == team][0]

    logging.info("Thread %s : getting match season", threading.current_thread().name)
    season = seasons.get(valMatch.get("matchInfo").get("seasonId"))

    logging.info("Thread %s : getting match date and time", threading.current_thread().name)
    date = datetime.datetime.fromtimestamp(valMatch.get("matchInfo").get("gameStartMillis")/1e3)

    logging.info("Thread %s : finding match mvp", threading.current_thread().name)
    mvp = get_mvp(val, valMatch)

    logging.info("Thread %s : gathering all data into dictionary", threading.current_thread().name)
    data =  {
                "Season" : season,
                "Win/Loss" : ("WIN" if win == True else "LOSS"),
                "Character" : character,
                "Rank" : rank,
                "Kills" : stats.get("kills"),
                "Keaths" : stats.get("deaths"),
                "Assists" : stats.get("assists"),
                "HS%" : headshotPercentage,
                "KAST%" : kastPercentage,
                "Date" : date.strftime("%d-%m-%Y %H:%M"),
                "Map" : matchMap,
                "MVP" : mvp
            }

    with LOCK:
        DATA.append(data)

def main():

    logdir = os.path.join(os.path.dirname(__file__), "./logs/")
    logpath = os.path.join(logdir, f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}.log")

    if not os.path.exists(logdir):
        os.makedirs(logdir)

    format = "%(asctime)s: %(message)s"
    logging.basicConfig(filename="tracker.log",filemode='w', format=format, level=logging.INFO, datefmt="%H:%M:%S")

    logging.info("Main  : accessing valorant local API")
    val = valApiAccess() 

    logging.info("Main  : getting valorant match history")
    matches = val.get_match_history()

    threads = list()

    logging.info("Main  : creating threads to process match info")
    for m in matches:
       x = threading.Thread(target=get_match_stats, args=(val, m))
       x.start()
       threads.append(x)

    logging.info("Main  : waiting for threads to finish operation")
    for thread in threads:
        thread.join()

    logging.info("Main  : adding data to dataframe")

    DATA_SORTED = sorted(DATA, key=lambda day : day["Date"])
    df = pd.DataFrame(DATA_SORTED)
    df.index += 1
    df.index.name = "Game"

    print(df)

    logging.info("Main  : saving data to csv file")

    df.to_csv("./matches.csv", mode="a", header=False)

    logging.info("Main  : finishing program")

if __name__ == "__main__":
    main()