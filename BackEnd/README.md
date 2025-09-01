# Gamified Ranking System - Backend

This is the backend service for the Gamified Ranking System, built with FastAPI and MongoDB.

## Prerequisites

- Python 3.8+
- MongoDB (running locally on default port 27017)

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Ranking-Page/BackEnd
   ```

2. **Set up virtual environment** (Windows)
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   .\venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. **Start MongoDB**
   - Make sure MongoDB is running on your system

2. **Run the FastAPI server**
   ```bash
   uvicorn main:app --reload
   ```

3. **Access the API documentation**
   - Open your browser and go to: http://localhost:8000/docs

## API Endpoints

- `GET /api/leaderboard` - Get leaderboard data
- `GET /api/members/{member_id}` - Get member details
- `POST /api/members/{member_id}/contributions` - Add a new contribution

## Project Structure

```
BackEnd/
├── database.py       # Database connection and setup
├── main.py          # FastAPI application entry point
├── models/          # Data models
│   └── models.py
├── routes/          # API routes
│   ├── __init__.py
│   ├── leaderboard.py
│   ├── members.py
│   └── contributions.py
└── utils.py         # Helper functions
```

## Development

- **Virtual Environment**: Always activate the virtual environment before working on the project
- **Environment Variables**: Create a `.env` file for local development if needed
- **Testing**: Run tests with `pytest` (coming soon)

## Deployment

For production deployment, consider using:
- Gunicorn as the production server
- Environment variables for configuration
- Proper logging and monitoring
