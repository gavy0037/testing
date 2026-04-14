from fastapi import APIRouter, UploadFile, File, WebSocket, Request
from utils import facial_recognition_module
from pymongo import MongoClient
import pymysql
import os
from dotenv import load_dotenv
import json


load_dotenv()
login_router = APIRouter()

@login_router.post("/login")
async def get_image(request: Request, image: UploadFile = File(...)):
    image_data = await image.read()

    client = MongoClient(os.getenv("MONGO_HOST"))
    db = client["tic_tac_toe_iiith"]
    
    connection = pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER") or "root",
        password=os.getenv("MYSQL_USER_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD"),

        port=int(os.getenv("MYSQL_PORT"))
    )
    cursor = connection.cursor()
    
    cursor.execute("USE tic_tac_toe_iiith")
    # 1. Load faces from MongoDB
    profileDict = {}
    for doc in db["profiles"].find():
        if doc["uid"] != "2025101125" and doc["uid"] != "2025101084" and doc["uid"] != "2025111008" and doc["uid"] != "2025101121" and doc["uid"] != "2025101134" and doc["uid"] != "2025101140": 
            continue
        uid = doc["uid"]
        imageBinary = doc["image"]

        profileDict[uid] = imageBinary

    closestMatch = facial_recognition_module.find_closest_match(image_data, profileDict)

    if closestMatch:
        cursor.execute('SELECT name FROM players WHERE uid = %s', (closestMatch,))
        result = cursor.fetchone()
        student_name = result[0] if result else "Unknown Student"

        # Mark them as online
        cursor.execute("UPDATE players SET is_online = 1 WHERE uid=%s", (closestMatch,))
        connection.commit()
        connection.close()

        # Set the server-side session — sends a signed cookie to the browser
        request.session["uid"] = closestMatch
        request.session["name"] = student_name

        # SUCCESS: This is what the JavaScript 'fetch' is waiting for
        return {
            "status": "success", 
            "uid": closestMatch, 
            "name": student_name
        }
    
    else:
        connection.close()
        # FAILURE: Tell the browser it failed
        return {
            "status": "failure", 
            "message": "Face not recognized"
        }