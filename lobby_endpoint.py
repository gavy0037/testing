from fastapi import APIRouter, UploadFile, File,WebSocket

from pymongo import MongoClient
import pymysql

import os
from dotenv import load_dotenv

load_dotenv()
import json
from manager.lobby_manager import manager 

def get_db_conn():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER") or "root",
        password=os.getenv("MYSQL_USER_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD"),
        database="tic_tac_toe_iiith",
        port=int(os.getenv("MYSQL_PORT"))
    )
def get_online_players():
    connection = pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER") or "root",
        password=os.getenv("MYSQL_USER_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD"),
        database="tic_tac_toe_iiith",
        port=int(os.getenv("MYSQL_PORT"))
    )
    cursor = connection.cursor()

    # 2. Ask for everyone who is currently online
    cursor.execute("SELECT uid, name FROM players WHERE is_online = 1")
    
    # 3. Format the data into a list of dictionaries
    players = []
    for (uid, name) in cursor.fetchall():
        players.append({"uid": uid, "name": name})
    
    connection.close()
    return players

def get_leaderboard():
    connection = get_db_conn()
    cursor = connection.cursor()
    cursor.execute("SELECT uid, name, elo_rating FROM players ORDER BY elo_rating DESC")
    leaderboard = []
    for (uid, name, elo_rating) in cursor.fetchall():
        leaderboard.append({"uid": uid, "name": name, "elo_rating": elo_rating})
    connection.close()
    return leaderboard

lobby_router = APIRouter()


@lobby_router.websocket("/ws/lobby")
async def lobby_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    current_user_uid = None 
    
    try:
        while True:
            data = await websocket.receive_json()

            if data["type"] == "join":
                current_user_uid = data["uid"]  # only 'join' has uid
                manager.user_websockets[current_user_uid] = websocket
                
                conn = get_db_conn()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("UPDATE players SET is_online = 1 WHERE uid=%s", (current_user_uid,))
                        conn.commit()
                finally:
                    conn.close()

                online_players = get_online_players() 

                await manager.broadcast({
                    "type": "player_list", 
                    "players": online_players
                })

                await manager.broadcast({
                    "type": "leaderboard",
                    "players": get_leaderboard()
                })
            # --- HANDLE CHALLENGE REQUEST ---
            elif data["type"] == "challenge_request":
                target_uid = data["to_player"]
                from_uid = data["from_player"]
                
                conn = get_db_conn()
                challenger_name = "Unknown"
                try:
                    with conn.cursor() as cursor:
                        cursor.execute('SELECT name FROM players WHERE uid = %s', (from_uid,))
                        row = cursor.fetchone()
                        if row:
                            challenger_name = row[0]
                finally:
                    conn.close()

                if target_uid in manager.user_websockets:
                    await manager.send_personal_message({
                        "type": "incoming_challenge",
                        "from_uid": from_uid,
                        "from_name": challenger_name
                    }, manager.user_websockets[target_uid])

            # --- HANDLE CHALLENGE RESPONSE (New Logic) ---
            elif data["type"] == "challenge_response":
                challenger_uid = data["to_player"]
                responder_uid = data["from_player"]
                accepted = data["accepted"]

                if challenger_uid in manager.user_websockets:
                    challenger_socket = manager.user_websockets[challenger_uid]
                    
                    if accepted:
                        # Generate a unique room ID for the Tic-Tac-Toe match
                        game_id = f"game_{challenger_uid}_{responder_uid}"
                        
                        start_msg = {
                            "type": "game_start",
                            "game_id": game_id
                        }

                        # Tell BOTH players to switch to the game page
                        await manager.send_personal_message(start_msg, challenger_socket)
                        await manager.send_personal_message(start_msg, websocket) # The Responder
                    else:
                        # Notify the challenger that the request was declined
                        await manager.send_personal_message({
                            "type": "challenge_rejected",
                            "message": "The player declined your challenge."
                        }, challenger_socket)

    except Exception as e:
        print(f"Lobby Error: {e}")
    
    finally:
        # ALWAYS remove the socket — even if 'join' was never received
        if websocket in manager.active_connections:
            manager.active_connections.remove(websocket)

        if current_user_uid:
            conn = get_db_conn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE players SET is_online = 0 WHERE uid=%s", (current_user_uid,))
                    conn.commit()
            finally:
                conn.close()

            if current_user_uid in manager.user_websockets:
                del manager.user_websockets[current_user_uid]

            online_players = get_online_players()
            await manager.broadcast({
                "type": "player_list", 
                "players": online_players
            })
