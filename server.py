import asyncio
import json
import os
import random
import string
from aiohttp import web
from game import PositionComboGame

# --- Application State ---
# This will now hold all active game rooms
ROOMS = {}

# --- WebSocket Helper Functions (now room-aware) ---
async def broadcast(app, room_key, message):
    """Sends a message to all connected clients in a specific room."""
    if room_key in ROOMS and ROOMS[room_key]["websockets"]:
        await asyncio.gather(*[ws.send_json(message) for ws in ROOMS[room_key]["websockets"].values()])

async def send_to_player(player_id, room_key, message):
    """Sends a message to a specific player in a specific room."""
    if room_key in ROOMS:
        ws = ROOMS[room_key]["websockets"].get(player_id)
        if ws:
            await ws.send_json(message)

# --- Game Logic Message Handlers (now room-aware) ---
async def handle_new_game(app, room_key):
    game = ROOMS[room_key]["game"]
    print(f"[{room_key}] New game started. Entering synchronized placement phase.")
    await trigger_placement_turn(app, room_key)

async def trigger_placement_turn(app, room_key):
    game = ROOMS[room_key]["game"]
    if game.phase != 'placement': return
    current_number = game.placement_sequence[game.placement_step]
    print(f"[{room_key}] Triggering placement step {game.placement_step}, number: {current_number}")
    await broadcast(app, room_key, {
        "type": "new_placement_number", "number": current_number, "step": game.placement_step
    })
    await broadcast_gamestate(app, room_key)

async def handle_submit_placement(app, room_key, player_id, cell_id):
    game = ROOMS[room_key]["game"]
    result = game.submit_placement(player_id, cell_id)
    if "error" in result:
        await send_to_player(player_id, room_key, {"type": "error", "message": result["error"]})
        return
    
    print(f"[{room_key}] Player {player_id} placed number at {cell_id}.")
    await broadcast_gamestate(app, room_key)

    if result.get("status") == "next_placement_turn":
        await trigger_placement_turn(app, room_key)
    elif result.get("status") == "match_started":
        print(f"[{room_key}] Boards complete. Starting match phase.")
        await broadcast(app, room_key, {"type": "match_start", "message": "The match begins! Both players, choose your first combination."})

async def handle_submit_combination(app, room_key, player_id, cells):
    game = ROOMS[room_key]["game"]
    result = game.submit_combination(player_id, cells)
    if "error" in result:
        await send_to_player(player_id, room_key, {"type": "error", "message": result["error"]})
        return
    
    print(f"[{room_key}] Player {player_id} submitted combination for round {game.match_round}.")
    if result.get("status") == "round_resolved":
        print(f"[{room_key}] Both players submitted. Resolving round.")
        await broadcast(app, room_key, {"type": "round_result", "data": result})
    
    await broadcast_gamestate(app, room_key)

async def broadcast_gamestate(app, room_key):
    if room_key in ROOMS:
        game = ROOMS[room_key]["game"]
        state = game.get_game_state()
        await broadcast(app, room_key, {"type": "game_state", "data": state})

# --- aiohttp Request Handlers ---
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    room_key = None
    player_id = None
    
    try:
        # Step 1: Wait for the client to send a "join" message.
        first_msg = await ws.receive_json()
        action = first_msg.get("action")
        
        if action == "join":
            room_key = first_msg.get("room_key")
            if not room_key:
                await ws.close(code=4000, message=b'Room key is required.')
                return

            # Find or create the room
            if room_key not in ROOMS:
                is_test_mode = (room_key == "TEST")
                ROOMS[room_key] = {
                    "game": PositionComboGame(test_mode=is_test_mode),
                    "websockets": {}
                }
                print(f"New room created: {room_key} (Test Mode: {is_test_mode})")
            
            room = ROOMS[room_key]
            
            # Assign player ID
            if 'player1' not in room["websockets"]:
                player_id = 'player1'
            elif 'player2' not in room["websockets"]:
                player_id = 'player2'
            else:
                await ws.send_json({"type": "error", "message": "Game room is full."})
                await ws.close()
                return

            room["websockets"][player_id] = ws
            print(f"[{room_key}] Player {player_id} connected.")
            await send_to_player(player_id, room_key, {"type": "welcome", "player_id": player_id})
            
            # If room is now full, start the game (or send gamestate if test mode)
            if len(room["websockets"]) == 2:
                if room["game"].phase == 'match': # Test mode starts in match phase
                    await broadcast(request.app, room_key, {"type": "match_start", "message": "Test match started! Choose your first combination."})
                else: # Normal mode
                    await handle_new_game(request.app, room_key)

            await broadcast_gamestate(request.app, room_key)
        
        else:
            await ws.close(code=4001, message=b'First message must be a join action.')
            return

        # Step 2: Main message loop for gameplay
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                game_action = data.get('action')
                game = ROOMS[room_key]["game"]

                if game.phase == 'placement' and game_action == 'submit_placement':
                    await handle_submit_placement(request.app, room_key, player_id, data.get('cell_id'))
                elif game.phase == 'match' and game_action == 'submit_combination':
                    await handle_submit_combination(request.app, room_key, player_id, data.get('cells'))
            elif msg.type == web.WSMsgType.ERROR:
                print(f"[{room_key}] WebSocket connection closed with exception {ws.exception()}")

    finally:
        # Step 3: Cleanup on disconnection
        if room_key and player_id:
            print(f"[{room_key}] Player {player_id} disconnected.")
            room = ROOMS.get(room_key)
            if room and player_id in room["websockets"]:
                del room["websockets"][player_id]
                
                # If room is now empty, delete it
                if not room["websockets"]:
                    print(f"Room {room_key} is empty, deleting.")
                    del ROOMS[room_key]
                else:
                    # Notify remaining player
                    await broadcast(request.app, room_key, {"type": "player_disconnected", "player_id": player_id})

    return ws

# --- Application Setup ---
def create_app(argv=None):
    app = web.Application()
    app.router.add_get('/ws', websocket_handler)
    # Serve lobby.html at the root, and other files like index.html from the web dir
    app.router.add_get('/', lambda request: web.FileResponse('./web/lobby.html'))
    app.router.add_static('/static/', path='./web/', name='static')
    return app