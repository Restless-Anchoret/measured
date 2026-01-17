# Measured Backend

FastAPI backend for the Measured time tracking application.

## Setup

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
python3 -m pip install -r requirements.txt
```

3. Initialize the database with hardcoded projects:
```bash
python3 -m app.init_db
```

4. Run the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI) is available at `http://localhost:8000/docs`

## Testing

To run the integration tests, make sure you have activated the virtual environment and installed all dependencies (including test dependencies from `requirements.txt`).

Run all tests:
```bash
pytest
```

Run tests with verbose output:
```bash
pytest -v
```

Run a specific test file:
```bash
pytest tests/test_health.py
pytest tests/test_projects.py
pytest tests/test_sessions.py
```

Run a specific test:
```bash
pytest tests/test_sessions.py::test_create_session
```

The test suite uses a separate test database (automatically created and cleaned up) and includes integration tests for all API endpoints.

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/projects` - Get list of projects
- `POST /api/sessions` - Create a new session
- `GET /api/sessions?page=1&page_size=20` - Get paginated list of sessions
- `GET /api/sessions/{id}` - Get a single session by ID
- `PUT /api/sessions/{id}` - Update a session

## Database

The application uses SQLite by default (stored in `measured.db`). For production, you can set the `DATABASE_URL` environment variable to use a different database.

