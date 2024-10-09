import logging
from pymongo import MongoClient
from datetime import datetime, timedelta
import sys
import re
import asyncio

import config
from utils import log_config, inquirerpy
from src.database.mongo import mongo

DEV_MODE = config.DEV_MODE

PHONE_NUMBERS_DEV = [
    "+55 21 7506-8348"
]

NEW_TRIAL_TIME_DEV = 6

async def fix_mongo():
    data = await mongo.find("add_free_trial", {})
    for item in data:
        phone = item.get("client")
        added_date = item.get("added_date")
        added_by = item.get("added_by",item.get("prospector"))
        new_trial_entry = {
                "added_date": added_date,
                "added_by": added_by
            }
        if not added_date or not added_by:
            continue
        
        await mongo.update_one(
            "add_free_trial",
            {"client": phone},
            {
                "$push": {"trial_info": new_trial_entry},
                "$unset": {"added_date": "", "added_by": "", "prospector": ""}
            }
        )

if __name__ == "__main__":
    asyncio.run(fix_mongo())