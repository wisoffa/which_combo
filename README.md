# Position Combo Game

Position Combo is a 1v1, web-based memory and strategy board game.

## Game Rules

The game consists of two phases: a synchronized **Placement Phase** and a simultaneous-submission **Match Phase**.

### 1. Placement Phase
- The game presents a single random number (1-10) to both players.
- Both players must choose an empty cell on their own 5x5 grid to place the number.
- Once both players have placed the number, the next random number is revealed.
- This continues for 25 rounds until both players' boards are completely filled.

### 2. Match Phase
- After placement, both players' boards are hidden, even from themselves. The game becomes a test of memory.
- The match consists of 14 rounds.
- In each round, both players simultaneously choose and submit a 4-cell straight-line combination from memory. A confirmation dialog will appear before submitting.
- The results are revealed only after both players have submitted their choices.
- A player's score for the round is based on the hand ranking of the numbers on their **own** hidden board at the chosen cell locations.

### Scoring
- In each round of the match phase, the player with the higher-ranked hand wins 1 point.
- The loser gets 0 points.
- In case of a draw, both players get 0 points.
- The player with the most points after 14 rounds wins the game.

## Setup

1.  **Create and activate a virtual environment (optional but recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install dependencies:**
    From the `which_combo` directory, run:
    ```bash
    pip install -r requirements.txt
    ```

## Running for Development

You will need two terminals to run the game.

1.  **Terminal 1: Start the Game Server**
    Navigate to the `which_combo` directory and run:
    ```bash
    python3 server.py
    ```
    By default, this will start on `ws://localhost:8765`.

2.  **Terminal 2: Start the Web Server**
    Navigate to the `which_combo/web` directory and run:
    ```bash
    python3 -m http.server 8000
    ```

3.  **Play**
    Open two browser tabs and navigate to `http://localhost:8000`. The first tab will be Player 1, the second will be Player 2.

## Configuration (Environment Variables)

The game server can be configured by setting the following environment variables before running `server.py`:

- `HOST`: The hostname the WebSocket server should bind to. Defaults to `localhost`. For production, you would typically set this to `0.0.0.0`.
- `PORT`: The port for the WebSocket server. Defaults to `8765`.

**Example:**
```bash
export HOST=0.0.0.0
export PORT=8000
python3 server.py
```
