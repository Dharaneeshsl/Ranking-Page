# 🏆 Gamified Ranking System - Backend

A high-performance backend service for tracking member contributions and rankings, built with FastAPI and MongoDB.

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- MongoDB 4.4+ (running locally on default port 27017)
- Git (for version control)

### 🛠️ Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/Ranking-Page.git
   cd Ranking-Page/BackEnd
   ```

2. **Set up virtual environment**

   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Start MongoDB**
   - Make sure MongoDB is running on your system
   - Default connection: `mongodb://localhost:27017`

5. **Run the application**

   ```bash
   uvicorn main:app --reload
   ```

6. **Access the API documentation**
   - Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Alternative docs: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 📊 Features

- **Points System**
  - Attend events, volunteer, lead events, upload docs, and bring sponsorships
  - Automatic point calculation based on contribution type

- **Level Progression**
  - Bronze (0-50 pts) → Silver (51-150) → Gold (151-300) → Platinum (300+)
  - Automatic level upgrades

- **Leaderboard**
  - Real-time ranking of members
  - Filter by time period (monthly/quarterly/yearly)

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/leaderboard` | Get ranked member list |
| `GET` | `/api/members/{id}` | Get member details |
| `POST` | `/api/members/{id}/contributions` | Add new contribution |
| `GET` | `/api/members` | List all members |

## 🏗️ Project Structure

```text
BackEnd/
├── database.py       # MongoDB connection and setup
├── main.py          # FastAPI app and routes
├── models/          # Data models and schemas
│   └── models.py
├── routes/          # API route handlers
│   ├── __init__.py
│   ├── leaderboard.py
│   ├── members.py
│   └── contributions.py
├── utils.py         # Helper functions
└── requirements.txt # Project dependencies
```

## 🧪 Testing

Run the test suite:

```bash
pytest
```

## 🚀 Deployment

For production deployment:

1. Set environment variables:

   ```env
   MONGODB_URI=your_mongodb_uri
   ENVIRONMENT=production
   ```

2. Install production dependencies:

   ```bash
   pip install gunicorn uvicorn[standard]
   ```

3. Run with Gunicorn:

   ```bash
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Credits

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Data stored in [MongoDB](https://www.mongodb.com/)
- Powered by Python 🐍
