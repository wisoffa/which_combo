# Position Combo Game

Position Combo is a 1v1, web-based memory and strategy board game.

## Game Rules

The game consists of two phases: a synchronized **Placement Phase** and a simultaneous-submission **Match Phase**.

### 1. Placement Phase
- The game presents a single random number (1-10) to both players.
- Both players must choose an empty cell on their own 5x5 grid to place the number.
- Once both players have placed the number, the next random number is revealed.
- This continues for 25 rounds until both players' boards are completely filled.
- **New Feature: Placement Notification**: When your opponent places a number, you will receive a temporary on-screen notification (e.g., "Opponent placed 5 in C3!") to keep you informed of their moves.

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

The application now runs as a single, unified server process and features a game lobby.

1.  **Start the Server**
    Navigate to the `which_combo` directory and run:
    ```bash
    python3 -m aiohttp.web -H localhost -P 8080 server:create_app
    ```

2.  **Play**
    - Open your browser and navigate to `http://localhost:8080`. You will be at the lobby.
    - **To start a game:** Click "Create New Game". A new game room will be created, and your URL will change to include the room key (e.g., `.../static/index.html?room=ABCDE`).
    - **To join a game:** Copy the `ABCDE` room key from the first player's URL, paste it into the "Enter Room Key" field on the second player's lobby page, and click "Join Game".

### Testing the Match Phase
To quickly test the match phase without going through all 25 placement rounds, you can use the test mode:
- On the lobby page, click the **Start Test Game** button.
- This will create and join a special room named "TEST" where both players start immediately in the match phase with randomly generated boards.
- To have a second player join the test game, have them also click "Start Test Game" or manually join the room with the key "TEST".

## Deployment to Google Cloud Run

This guide explains how to deploy the game to Google Cloud Run, a fully managed, serverless platform.

### Prerequisites
1.  Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud` CLI).
2.  Authenticate the CLI: `gcloud auth login`.
3.  Set your project: `gcloud config set project YOUR_PROJECT_ID`.
4.  Enable the Cloud Build and Artifact Registry APIs for your project.

### Deployment Steps

1.  **Build the Container Image**
    Navigate to the `which_combo` directory. Run the following command to use Cloud Build to create your container image and push it to the Artifact Registry. Replace `YOUR_PROJECT_ID` with your actual GCP Project ID.

    ```bash
    gcloud builds submit . --tag gcr.io/YOUR_PROJECT_ID/position-combo
    ```

2.  **Deploy to Cloud Run**
    Deploy the container image to Cloud Run. This command creates a public service and enables **session affinity**, which is crucial for ensuring WebSocket connections are stable.

    Replace `YOUR_PROJECT_ID` and choose a `YOUR_REGION` (e.g., `us-central1`).

    ```bash
    gcloud run deploy position-combo \
      --image gcr.io/YOUR_PROJECT_ID/position-combo \
      --platform managed \
      --region YOUR_REGION \
      --session-affinity \
      --allow-unauthenticated
    ```

3.  **Play Online**
    After deployment is successful, the command will output a public **Service URL**. Navigate to this URL to access the game lobby. Share a room key between two players to start a game.