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

Because the development server is not unified, you need two terminals to run the game locally. For production, this is handled by a single server process.

1.  **Terminal 1: Start the Python Backend**
    Navigate to the `which_combo` directory and run:
    ```bash
    python3 -m aiohttp.web -H localhost -P 8080 server:app
    ```

2.  **Play**
    Open two browser tabs and navigate to `http://localhost:8080`. The application is now served from a single port.

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
    gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/position-combo
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
    After deployment is successful, the command will output a public **Service URL** (e.g., `https://position-combo-xxxxxxxx-uc.a.run.app`).

    Simply navigate to this URL in two different browser tabs to play your production-level game! The frontend will automatically connect to the WebSocket on the same domain.
