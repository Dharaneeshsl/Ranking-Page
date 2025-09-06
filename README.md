# Ranking Page Application

A full-stack application for managing and displaying member rankings and contributions.

## 🚀 Features

- **Member Management**: Add, view, and manage members
- **Contribution Tracking**: Record and track member contributions
- **Leaderboard**: Real-time ranking system
- **Secure Authentication**: Session-based authentication
- **Responsive Design**: Works on desktop and mobile

## 🛠 Tech Stack

### Backend

- **Framework**: FastAPI
- **Database**: MongoDB
- **Authentication**: Session-based
- **Containerization**: Docker
- **Deployment**: Ready for production

### Frontend

- **Framework**: React.js
- **UI Library**: Material-UI
- **State Management**: Context API
- **Styling**: CSS3 with animations

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- MongoDB
- Docker (optional)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/Dharaneeshsl/Ranking-Page.git
   cd Ranking-Page
   ```

2. **Backend Setup**

   ```bash
   cd BackEnd
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Unix or MacOS:
   # source venv/bin/activate
   
   pip install -r requirements.txt
   ```

3. **Frontend Setup**

   ```bash
   cd ../FrontEnd/RankingPage
   npm install
   ```

## 🚀 Running Locally

### Using Docker (Recommended)

```bash
docker-compose up --build
```

### Manual Start

1. **Start Backend**

   ```bash
   cd BackEnd
   uvicorn main:app --reload
   ```

2. **Start Frontend**

   ```bash
   cd FrontEnd/RankingPage
   npm start
   ```

## 🌐 API Documentation

Once the backend is running, access the API documentation at:

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

## 🔒 Security

- All passwords are hashed using bcrypt
- Secure session management with HTTP-only cookies
- Environment variables for sensitive data
- CORS protection
- Rate limiting in production

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📧 Contact

For any questions or feedback, please open an issue or contact the maintainers.
