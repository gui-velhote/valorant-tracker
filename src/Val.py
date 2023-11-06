#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import json
import base64
import os
from requests import HTTPError
import threading

# Global constants
LOCKFILE_PATH = os.getenv("LOCALAPPDATA")
RESOURCES_PATH = "./resources"

class valApiAccess:

    def __init__(self):

        self.lockfile = self._parse_lockfile(self._get_lockfile())
        self.PORT = self.lockfile.get("port")
        self.PASSWORD = self.lockfile.get("password")

        self.ENTITLEMENTS_TOKEN, self.AUTH_TOKEN = self._get_entitlements_token()
        self.BASIC_HEADER = "Basic " + str(base64.b64encode(("riot:" + self.PASSWORD).encode('ascii'))).removeprefix('b').replace("\'", "")
        self.BEARER_HEADER = "Bearer " + self.AUTH_TOKEN

        self.PUUID, self.GAME_NAME = self._get_puuid()
        self.SHARD = self._get_shard()

        self._load_characters()
        self._load_maps()
        self._load_ranks()
        self._load_seasons()
        
    def _parse_lockfile(self,lockfile):

        parsed =    {  
                        "name"      : lockfile[0],
                        "pid"       : lockfile[1],
                        "port"      : lockfile[2],
                        "password"  : lockfile[3],
                        "protocol"  : lockfile[4]
                    }

        return parsed

    def _get_lockfile(self):


        with open(f"{LOCKFILE_PATH}/Riot Games/Riot Client/config/lockfile", "r", encoding="utf-8") as f:
            lockfile = f.read().split(":")
            f.close()
        
        return lockfile
    
    def _get_entitlements_token(self):
        
        header_auth = "riot:" + self.PASSWORD
        header_auth_b64 = "Basic " + str(base64.b64encode(header_auth.encode('ascii'))).removeprefix('b').replace("\'", "")

        header = {"Authorization" : header_auth_b64}

        r = requests.get(f"https://127.0.0.1:{self.PORT}/entitlements/v1/token", headers=header, verify=False)
        response = json.loads(r.text)

        return response.get("token"), response.get("accessToken")

    def _get_shard(self):

        header = {"Authorization" : self.BASIC_HEADER}
        
        r = requests.get(f"https://127.0.0.1:{self.PORT}/riotclient/region-locale", headers=header, verify=False)

        region = json.loads(r.text).get("region")

        with open(RESOURCES_PATH + "/shards.json", "r") as f:
            SHARDS = json.loads(f.read())
            f.close()

        shard = None

        for s in SHARDS:
            for r in s.get("regions"):
                if r == region.lower():
                    shard = s.get("shard")
                    break

        return shard

    def _get_puuid(self):

        header = {"Authorization" : self.BASIC_HEADER}

        r = requests.get(f"https://127.0.0.1:{self.PORT}/chat/v1/session", headers=header, verify=False)
        puuid = json.loads(r.text).get("puuid")
        game_name = json.loads(r.text).get("game_name")
        return puuid, game_name

    def _update_match_history(self):
        
        header =    {
                        "X-Riot-Entitlements-JWT"   : self.ENTITLEMENTS_TOKEN,
                        "Authorization"             : self.BEARER_HEADER
                    }

        r = requests.get(f"https://pd.{self.SHARD}.a.pvp.net/match-history/v1/history/{self.PUUID}?endIndex=20&queue=competitive", headers=header)

        matches = json.loads(r.text).get("History")
        newMatches = []

        if os.path.exists(RESOURCES_PATH + "/matches.json"):
            with open(RESOURCES_PATH + "/matches.json", "r") as f:
                existingMatches = json.loads(f.read())
                f.close()

            for valMatch in matches:
                if valMatch not in existingMatches:
                    existingMatches.append(valMatch)
                    newMatches.append(valMatch)
                
        else:
            existingMatches = matches
            newMatches = matches

        with open(RESOURCES_PATH + "/matches.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(existingMatches))
            f.close()

        return newMatches 
    
    def get_match_history(self):

        newMatches = self._update_match_history()

        return [x.get("MatchID") for x in newMatches]

    def get_match_details(self, matchId):

        header =    {
                        "X-Riot-Entitlements-JWT"   : self.ENTITLEMENTS_TOKEN,
                        "Authorization"             : self.BEARER_HEADER
                    }

        r = requests.get(f"https://pd.{self.SHARD}.a.pvp.net/match-details/v1/matches/{matchId}", headers=header)

        valMatch = json.loads(r.text)
        return valMatch

    def _load_maps(self):

        with open(RESOURCES_PATH + "/maps.json", "r") as f:
            self.maps = {m.get("mapUrl") : m.get("displayName") for m in json.loads(f.read())}
            f.close()

    def _load_characters(self):

        with open(RESOURCES_PATH + "/characters.json", "r") as f:
            self.characters = {c.get("uuid") : c.get("displayName") for c in json.loads(f.read())}
            f.close()

    def _load_ranks(self):

        with open(RESOURCES_PATH + "/ranks.json") as f:
            self.ranks = {r.get("tier") :    {
                                            "tierName"  : r.get("tierName"),
                                            "smallIcon" : r.get("smallIcon"),
                                            "largeIcon" : r.get("largeIcon") 
                                        }
                                        for r in json.loads(f.read())}
            f.close()
        
    def _load_seasons(self):

        with open(RESOURCES_PATH + "/seasons.json", "r") as f:
            self.seasons = json.loads(f.read())
            f.close()

class valUpdater:

    def _update_seasons(self):

        EPISODE_STRING = "EPISODE"
        SPACE = " "

        r = requests.get("https://valorant-api.com/v1/seasons")
        data = json.loads(r.text).get("data")

        seasons = {}

        episode = ""

        for d in reversed(data):
            if EPISODE_STRING in d.get("displayName"):
                episode = d.get("displayName")
            elif d.get("displayName") == "Closed Beta":
                seasons[d.get("uuid")] = d.get("displayName")
            else:
                seasons[d.get("uuid")] = episode + SPACE + d.get("displayName")

        with open(RESOURCES_PATH + "/seasons.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(seasons))
            f.close()

    def _update_characters(self):

        r = requests.get("https://valorant-api.com/v1/agents")
        agents = json.loads(r.text).get("data")

        with open(RESOURCES_PATH + "/characters.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(agents))
            f.close()

    def _update_maps(self):
        
        r = requests.get("https://valorant-api.com/v1/maps")
        maps = json.loads(r.text).get("data")

        with open(RESOURCES_PATH + "/maps.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(maps))
            f.close()

    def _update_characters(self):

        r = requests.get("https://valorant-api.com/v1/competitivetiers")
        ranks = json.loads(r.text).get("data")[-1].get("tiers")

        with open(RESOURCES_PATH + "/ranks.json", "w") as f:
            f.write(json.dumps(ranks))
            f.close()


    def update_assets(self):
        self._update_characters()
        self._update_maps()
        self._update_seasons()