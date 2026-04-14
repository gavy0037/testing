from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from manager.room_manager import room_connection_manager, check_win_or_draw
from manager.lobby_manager import manager as lobby_manager
from api.lobby_endpoint import get_leaderboard
from script.update_rating import update_rating

game_router = APIRouter()

@game_router.websocket("/ws/room/{room_id}")
async def room_endpoint(room_id : str , websocket : WebSocket):
    # ── Security gate: read identity from the signed session cookie ──
    user_uid = websocket.session.get("uid")
    if not user_uid:
        await websocket.accept()
        await websocket.close(code=1008, reason="Not authenticated")
        return

    room_obj = await room_connection_manager.connect(websocket , room_id)
    if not room_obj:
        return

    # Store the authenticated UID in the room's uid map
    room_obj.uids[websocket] = user_uid

    try:
        while True :
            data = await websocket.receive_json()
            if data["type"] == "move":
                idx = int(data["index"])
                if websocket not in room_obj.players:
                    continue
                symbol = room_obj.players[websocket]

                # turn validation
                if room_obj.turn != symbol:
                    await websocket.send_json({"type":"error" , "message" : "Not your turn"})
                    continue  # FIX: was missing, code fell through
                
                # cell validation
                if room_obj.board[idx] != '_':
                    await websocket.send_json({"type":"error" , "message": "Cell already occupied"})
                    continue  # FIX: was missing
                
                # game over check
                if room_obj.game_over:
                    await websocket.send_json({"type":"error" , "message": "Game is over"})
                    continue

                # update state
                room_obj.board[idx] = symbol
                room_obj.turn = "O" if symbol == "X" else "X"

                # broadcast move to both players
                for conn in room_obj.connection:
                    await conn.send_json({
                        "type": "move",
                        "index": idx,
                        "symbol": symbol,
                        "your_turn": room_obj.players[conn] == room_obj.turn
                    })

                # winner check
                result = check_win_or_draw(room_obj, symbol)
                if result == 1:
                    room_obj.game_over = True
                    for conn in room_obj.connection:
                        await conn.send_json({"type":"result" , "status":"win" , "winner": symbol})


                    # update the ratings in sql base
                    opp_uid = ""
                    for ws,uid in room_obj.uids.items() :
                        if ws != websocket:
                            opp_uid = uid
                    self_uid = room_obj.uids[websocket]
                    update_rating(1.0,self_uid,opp_uid)
                    await lobby_manager.broadcast({"type": "leaderboard", "players": get_leaderboard()})

                    if room_id in room_connection_manager.room_list:
                        del room_connection_manager.room_list[room_id]
                elif result == 2:
                    room_obj.game_over = True
                    for conn in room_obj.connection:
                        await conn.send_json({"type":"result" , "status":"draw" , "winner": None})

                    opp_uid = ""
                    for ws,uid in room_obj.uids.items() :
                        if ws != websocket:
                            opp_uid = uid
                    self_uid = room_obj.uids[websocket]
                    update_rating(0.5,self_uid,opp_uid)
                    await lobby_manager.broadcast({"type": "leaderboard", "players": get_leaderboard()})

                    if room_id in room_connection_manager.room_list:
                        del room_connection_manager.room_list[room_id]

    except WebSocketDisconnect:
        # Check if they abandoned an active game (not just leaving after winning/drawing)
        if not room_obj.game_over and websocket in room_obj.uids:
            room_obj.game_over = True 
            
            opp_uid = ""
            for ws, uid in room_obj.uids.items():
                if ws != websocket:
                    opp_uid = uid
            
            self_uid = room_obj.uids[websocket]
            
            # Only apply forfeit if the other person was actually connected
            if opp_uid:
                update_rating(0.0, self_uid, opp_uid)
                await lobby_manager.broadcast({"type": "leaderboard", "players": get_leaderboard()})

        await room_connection_manager.disconnect(websocket , room_id)