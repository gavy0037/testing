import csv,requests,pymysql
from pymongo import MongoClient
from bson import Binary

import os
from dotenv import load_dotenv

load_dotenv()

mongoDBLink = os.getenv("MONGO_HOST")
client = MongoClient(mongoDBLink)
database = client["tic_tac_toe_iiith"]
profiles = database["profiles"]


connect=pymysql.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER") or "root",
    password=os.getenv("MYSQL_USER_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD"),
    port=int(os.getenv("MYSQL_PORT"))
)

cursor=connect.cursor()
cursor.execute("create database if not exists tic_tac_toe_iiith")
cursor.execute("USE tic_tac_toe_iiith")

cursor.execute("create table if not exists players(uid varchar(50) primary key,name varchar(50) default NULL,elo_rating int default 1200,is_online boolean default false)")
connect.commit()
cursor.execute('''create table if not exists games (
    game_id INT AUTO_INCREMENT PRIMARY KEY,
    player1_id VARCHAR(50),
    player2_id VARCHAR(50),
    board_state VARCHAR(9) DEFAULT "_________",
    current_turn VARCHAR(50),
    status VARCHAR(20) DEFAULT "waiting",
    FOREIGN KEY (player1_id) REFERENCES players(uid),
    FOREIGN KEY (player2_id) REFERENCES players(uid)
)''')
connect.commit()

# whenever this script is run again , all the player's rating will go to default and the players will go offline
cursor.execute("UPDATE players SET is_online = 0")
cursor.execute("UPDATE players SET elo_rating = 1200")
connect.commit()

with open("batch_data.csv", mode="r") as file:
    data=csv.DictReader(file)
    for row in data:
        url = "http://" + row["website_url"] + "/images/pfp.jpg"
        response=requests.get(url,timeout=5)
        
        
        if response.status_code == 200:
            cursor.execute("insert ignore into players(uid,name) values (%s,%s)",(row["uid"],row["name"]))
            connect.commit()
            image_data = response.content 
            doc={
                "uid": row["uid"],
                "image": Binary(image_data)
            }
            profiles.update_one(
                {"uid": row["uid"]},
                {"$set": doc},
                upsert=True
            )
            print(f"Record for the student with id {row["uid"]} is successfully created")
        else:
            print(f"Failed to fetch data for {row["uid"]}. Status: {response.status_code}")
connect.close()
client.close()