#!/usr/bin/python
# -*- coding: utf-8 --

import os
import Val
import json

def _generate_shards():
    SHARDS =    [
                    {"shard" : "na", "regions" : ["na", "br", "latam"]},
                    {"shard" : "eu", "regions" : ["eu"]},
                    {"shard" : "ap", "regions" : ["ap"]},
                    {"shard" : "kr", "regions" : ["kr"]}
                ]
            
    with open("./resources/shards.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(SHARDS))
        f.close()

def main():
    if not os.path.exists("./resources"):
        os.makedirs("./resources")

    _generate_shards()

    valUpdater = Val.valUpdater()
    valUpdater.update_assets()


if __name__ == "__main__":
    main()