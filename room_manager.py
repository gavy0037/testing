from fastapi import WebSocket

class room:
    def __init__(self):
        self.connection : list[WebSocket] = []
        self.board : list[str] = ["_"]*9 # _ is for empty cell
        self.turn : str = "X" # whose turn it is
        self.game_over: bool = False
        self.players : dict[WebSocket, str] = {}# this is to identify the player from websocket i.e. which websockets corresponds to X or O
        self.uids : dict[WebSocket,str] = {} # this is to get uid to update ratings from websockets

class room_manager:
    def __init__(self):
        self.room_list : dict[str,room] = {}

    async def connect(self , websocket: WebSocket , room_id: str):
        if room_id not in self.room_list:
            self.room_list[room_id] = room()

        currRoom = self.room_list[room_id]
        # Assign symbol based on what's already taken
        existing_symbols = list(currRoom.players.values())
        if 'X' not in existing_symbols:
            currRoom.players[websocket] = 'X'
        else:
            currRoom.players[websocket] = 'O'
        
        await websocket.accept()
        if len(self.room_list[room_id].connection) >= 2:
            await websocket.close(code=1008 , reason="room_full")
            return None
        
        currRoom.connection.append(websocket)

        # Send init message to this player
        symbol = currRoom.players[websocket]
        await websocket.send_json({"type": "init", "symbol": symbol, "message": f"You are Player {symbol}"})

        # If 2 players are in, notify both that game has started
        if len(currRoom.connection) == 2:
            for conn in currRoom.connection:
                await conn.send_json({"type": "start", "your_turn": currRoom.players[conn] == "X"})

        return currRoom

    async def disconnect(self , websocket: WebSocket , room_id: str):
        if room_id in self.room_list:
            curr_room = self.room_list[room_id]
            if websocket in curr_room.connection:
                curr_room.connection.remove(websocket)
            if websocket in curr_room.players:
                del curr_room.players[websocket]
        
            # if room is empty, delete it
            if len(curr_room.connection) == 0:
                del self.room_list[room_id]
            else:
                remaining = curr_room.connection[0]
                await remaining.send_json({"type": "system", "message": "Opponent disconnected. Returning to lobby..."})
                del self.room_list[room_id]
    
    async def broadcast(self , data: dict , room_id : str , sender: WebSocket):
        #here data is a json for game data
        if room_id in self.room_list:
            for oppenent in self.room_list[room_id].connection:
                if oppenent != sender:
                    await oppenent.send_json(data)

room_connection_manager = room_manager()

def check_win_or_draw(r : room , symbol: str) -> int:
    # this will check if the given symbol player is winning or not
    board = r.board
    filled_cells = 0
    count_in_main_diagonal = 0 
    count_in_other_diagonal = 0
    for i in range(0,3):
        count_in_row = 0
        count_in_col = 0
        for j in range(0,3):
            idx = i*3+j
            col_idx = j*3+i  # FIX: correct 1D index for column check
            if board[idx] != "_":
                filled_cells+=1
            if board[idx] == symbol:
                count_in_row+=1
            if board[col_idx] == symbol:  # FIX: was board[j][i]
                count_in_col+=1
            if j == i and board[idx] == symbol:
                count_in_main_diagonal+=1
            if j+i == 2 and board[idx] == symbol:
                count_in_other_diagonal+=1
        if count_in_row == 3 or count_in_col == 3:
            return 1
    if count_in_main_diagonal == 3 or count_in_other_diagonal == 3:
        return 1

    # now check for draw , i can just count number of unfilled cells , if 9 then it's a draw
    if filled_cells == 9 :
        return 2 
    
    return 0
