# TaskPilot

TaskPilot is a web-based application that uses an AI agent to automate tasks in a browser. The user provides a goal, and the agent plans and executes the steps to achieve it.

## Project Structure

- `frontend/`: Contains the frontend code (HTML, CSS, and JavaScript).
- `server/`: Contains the backend code (FastAPI application).

## Backend

The backend is a FastAPI application that provides a WebSocket API for the frontend to communicate with the AI agent.

### Key Components

- `main.py`: The main entry point of the FastAPI application.
- `agent/`: Contains the core logic of the AI agent.
  - `planner.py`: The agent's planner, which generates a plan of steps to achieve a given goal.
  - `executor.py`: The agent's executor, which executes the steps of the plan.
  - `models.py`: Pydantic models used by the agent.
- `config.py`: The application's configuration.

### Setup

1.  Install the required dependencies:

    ```bash
    pip install -r server/requirements.txt
    ```

2.  Install Playwright browsers (first time only):

    ```bash
    python -m playwright install
    ```

3.  Create a `.env` file in the root of the project and add the following environment variables:

    ```
    GROQ_API_KEY=your_groq_api_key
    ```

4.  Run the backend server:

    ```bash
    uvicorn server.main:app --reload
    ```

## Frontend

The frontend is a simple HTML page that connects to the backend via a WebSocket.

### Setup

1.  Install frontend dependencies and start the dev server:

    ```bash
    cd frontend
    npm install
    npm run dev
    ```

2.  Open the Vite URL it prints (default `http://localhost:5173`).

Optional: set `VITE_WS_URL` in `frontend/.env` if the backend runs on a different host/port.
