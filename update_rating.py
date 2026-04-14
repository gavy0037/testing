import pymysql
from pymongo import MongoClient

import os 
from dotenv import load_dotenv

load_dotenv()

def update_rating(result: float, self_uid : str, opponent_uid : str):

    '''
        result : 
        1-> win , 0.5 -> draw , 0 -> lose
    '''

    connect=pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER") or "root",
        password=os.getenv("MYSQL_USER_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD"),
        port=int(os.getenv("MYSQL_PORT"))
    )

    cursor=connect.cursor()

    cursor.execute("USE tic_tac_toe_iiith")

    # Fetch self rating
    cursor.execute("SELECT elo_rating FROM players WHERE uid=%s", (self_uid))
    self_rating_row = cursor.fetchone()
    self_rating = self_rating_row[0] if self_rating_row else 1200
    
    # Fetch opponent rating
    cursor.execute("SELECT elo_rating FROM players WHERE uid=%s", (opponent_uid))
    opponent_rating_row = cursor.fetchone()
    opponent_rating = opponent_rating_row[0] if opponent_rating_row else 1200

    self_win_probabilty = 1 / (1 + 10 ** ((opponent_rating - self_rating)/400))
    self_newRating = round(self_rating + 32 * (result - self_win_probabilty)) # round is done to maintain elo rating as integers

    # for opponent , the result is 1-self_result
    opponent_win_probability = 1 / (1 + 10 ** ((self_rating-opponent_rating)/ 400))
    opponent_newRating = round(opponent_rating +32 *((1-result)-opponent_win_probability))

    cursor.execute("UPDATE players SET elo_rating=%s WHERE uid=%s", (str(self_newRating), self_uid))
    cursor.execute("UPDATE players SET elo_rating=%s WHERE uid=%s", (str(opponent_newRating), opponent_uid))
    connect.commit()
    connect.close()