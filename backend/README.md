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

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/projects` - Get list of projects
- `POST /api/sessions` - Create a new session
- `GET /api/sessions?page=1&page_size=20` - Get paginated list of sessions
- `PUT /api/sessions/{id}` - Update a session

## Database

The application uses SQLite by default (stored in `measured.db`). For production, you can set the `DATABASE_URL` environment variable to use a different database.

