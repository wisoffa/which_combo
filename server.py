import asyncio
import json
import os
import websockets
from game import PositionComboGame

# --- Game State and Client Management ---
game = PositionComboGame()
clients = {}  # {websocket: player_id}
player_websockets = {'player1': None, 'player2': None}

async def broadcast(message):
    """Sends a message to all connected clients."""
    if clients:
        await asyncio.gather(*[client.send(json.dumps(message)) for client in clients])

async def send_to_player(player_id, message):
    """Sends a message to a specific player."""
    ws = player_websockets.get(player_id)
    if ws:
        await ws.send(json.dumps(message))

# --- Message Handlers ---
async def handle_new_game():
    """Starts a new game and initiates the synchronized placement phase."""
    global game
    game = PositionComboGame()
    print("New game started. Entering synchronized placement phase.")
    await trigger_placement_turn()

async def trigger_placement_turn():
    """Sends the next number to be placed to both players."""
    if game.phase != 'placement': return

    current_number = game.placement_sequence[game.placement_step]
    print(f"Triggering placement step {game.placement_step}, number: {current_number}")
    await broadcast({
        "type": "new_placement_number",
        "number": current_number,
        "step": game.placement_step
    })
    await broadcast_gamestate()

async def handle_submit_placement(player_id, cell_id):
    """Handles a single placement from a player."""
    result = game.submit_placement(player_id, cell_id)
    
    if "error" in result:
        await send_to_player(player_id, {"type": "error", "message": result["error"]})
        return
    
    print(f"Player {player_id} placed number at {cell_id}.")
    await broadcast_gamestate()

    if result.get("status") == "next_placement_turn":
        await trigger_placement_turn()
    elif result.get("status") == "match_started":
        print("Both players' boards are complete. Starting match phase.")
        await broadcast({
            "type": "match_start",
            "message": "The match begins! Both players, choose your first combination."
        })

async def handle_submit_combination(player_id, cells):
    """Handles a player's combination submission for the round."""
    result = game.submit_combination(player_id, cells)
    
    if "error" in result:
        await send_to_player(player_id, {"type": "error", "message": result["error"]})
        return

    print(f"Player {player_id} submitted their combination for round {game.match_round}.")
    
    if result.get("status") == "round_resolved":
        print("Both players have submitted. Resolving round.")
        await broadcast({"type": "round_result", "data": result})
    
    await broadcast_gamestate()

async def broadcast_gamestate():
    """Broadcasts the current state of the game to all players."""
    state = game.get_game_state()
    await broadcast({"type": "game_state", "data": state})

# --- WebSocket Connection Handler ---
async def handler(websocket):
    """Manages WebSocket connections, assigns players, and processes messages."""
    global game
    player_id = None
    try:
        if player_websockets['player1'] is None:
            player_id = 'player1'
        elif player_websockets['player2'] is None:
            player_id = 'player2'
        else:
            await websocket.send(json.dumps({"type": "error", "message": "Game is full."}))
            return

        clients[websocket] = player_id
        player_websockets[player_id] = websocket
        print(f"Player {player_id} connected.")
        await send_to_player(player_id, {"type": "welcome", "player_id": player_id})

        if all(p is not None for p in player_websockets.values()):
            await handle_new_game()

        async for message in websocket:
            data = json.loads(message)
            action = data.get('action')

            if game.phase == 'placement' and action == 'submit_placement':
                await handle_submit_placement(player_id, data.get('cell_id'))
            elif game.phase == 'match' and action == 'submit_combination':
                await handle_submit_combination(player_id, data.get('cells'))
    finally:
        print(f"Player {player_id} disconnected.")
        if websocket in clients:
            del clients[websocket]
        if player_id:
            player_websockets[player_id] = None
        if any(p is not None for p in player_websockets.values()):
            await broadcast({"type": "player_disconnected", "player_id": player_id})
        print("Resetting game due to disconnection.")
        game = PositionComboGame()


async def main():
    """Starts the WebSocket server using environment variables for configuration."""
    host = os.environ.get("HOST", "localhost")
    port = int(os.environ.get("PORT", 8765))
    async with websockets.serve(handler, host, port):
        print(f"Server started at ws://{host}:{port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())