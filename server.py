import asyncio
import json
import os
from aiohttp import web
from game import PositionComboGame

# --- Application State ---
game = PositionComboGame()
clients = {}  # {websocket: player_id}
player_websockets = {'player1': None, 'player2': None}

# --- WebSocket Helper Functions ---
async def broadcast(app, message):
    """Sends a message to all connected clients."""
    if clients:
        await asyncio.gather(*[ws.send_json(message) for ws in clients])

async def send_to_player(player_id, message):
    """Sends a message to a specific player."""
    ws = player_websockets.get(player_id)
    if ws:
        await ws.send_json(message)

# --- Game Logic Message Handlers ---
async def handle_new_game(app):
    """Starts a new game and initiates the synchronized placement phase."""
    global game
    game = PositionComboGame()
    print("New game started. Entering synchronized placement phase.")
    await trigger_placement_turn(app)

async def trigger_placement_turn(app):
    if game.phase != 'placement': return
    current_number = game.placement_sequence[game.placement_step]
    print(f"Triggering placement step {game.placement_step}, number: {current_number}")
    await broadcast(app, {
        "type": "new_placement_number",
        "number": current_number,
        "step": game.placement_step
    })
    await broadcast_gamestate(app)

async def handle_submit_placement(app, player_id, cell_id):
    result = game.submit_placement(player_id, cell_id)
    if "error" in result:
        await send_to_player(player_id, {"type": "error", "message": result["error"]})
        return
    
    print(f"Player {player_id} placed number at {cell_id}.")
    await broadcast_gamestate(app)

    if result.get("status") == "next_placement_turn":
        await trigger_placement_turn(app)
    elif result.get("status") == "match_started":
        print("Boards complete. Starting match phase.")
        await broadcast(app, {
            "type": "match_start",
            "message": "The match begins! Both players, choose your first combination."
        })

async def handle_submit_combination(app, player_id, cells):
    result = game.submit_combination(player_id, cells)
    if "error" in result:
        await send_to_player(player_id, {"type": "error", "message": result["error"]})
        return
    
    print(f"Player {player_id} submitted combination for round {game.match_round}.")
    if result.get("status") == "round_resolved":
        print("Both players have submitted. Resolving round.")
        await broadcast(app, {"type": "round_result", "data": result})
    
    await broadcast_gamestate(app)

async def broadcast_gamestate(app):
    state = game.get_game_state()
    await broadcast(app, {"type": "game_state", "data": state})

# --- aiohttp Request Handlers ---
async def websocket_handler(request):
    """Handles new WebSocket connections."""
    global game  # Declare global at the top of the function
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    player_id = None
    try:
        if player_websockets['player1'] is None:
            player_id = 'player1'
        elif player_websockets['player2'] is None:
            player_id = 'player2'
        else:
            await ws.send_json({"type": "error", "message": "Game is full."})
            await ws.close()
            return

        clients[ws] = player_id
        player_websockets[player_id] = ws
        print(f"Player {player_id} connected.")
        await send_to_player(player_id, {"type": "welcome", "player_id": player_id})

        if all(p is not None for p in player_websockets.values()):
            await handle_new_game(request.app)

        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                action = data.get('action')

                if game.phase == 'placement' and action == 'submit_placement':
                    await handle_submit_placement(request.app, player_id, data.get('cell_id'))
                elif game.phase == 'match' and action == 'submit_combination':
                    await handle_submit_combination(request.app, player_id, data.get('cells'))
            elif msg.type == web.WSMsgType.ERROR:
                print(f"WebSocket connection closed with exception {ws.exception()}")

    finally:
        print(f"Player {player_id} disconnected.")
        if ws in clients:
            del clients[ws]
        if player_id:
            player_websockets[player_id] = None
        if any(p is not None for p in player_websockets.values()):
            await broadcast(request.app, {"type": "player_disconnected", "player_id": player_id})
        
        # Reset game if it's not full
        if not all(p is not None for p in player_websockets.values()):
             print("Resetting game due to disconnection.")
             game = PositionComboGame()

    return ws

# --- Application Setup ---
def create_app(argv=None):
    app = web.Application()
    app.router.add_get('/ws', websocket_handler)
    app.router.add_static('/', path='./web/', name='static', show_index=True)
    return app
