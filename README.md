## FastAPI Integration

### Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run the API: `python start_api.py`

### Endpoints

- `POST /api/agent/run` - Start the web scraping agent
- `POST /api/agent/stop` - Stop the agent
- `POST /api/agent/results` - Store agent results
- `POST /api/agent/error` - Store agent errors
- `GET /api/health` - Health check

### Features

- Multiprocessing agent execution
- 5-attempt retry mechanism
- Direct PDF download to bills folder
- Non-blocking API responses
