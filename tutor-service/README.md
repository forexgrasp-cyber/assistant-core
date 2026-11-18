# Tutor Service - Award-winning Language Learning Platform

A modern, full-featured language learning platform with AI-powered tutor, supporting 70+ languages with full verbal and written communication capabilities.

## Features

### 🎯 Core Learning
- **70+ Languages** - From Spanish to Swahili
- **CEFR A1-C2** - Structured curriculum across all proficiency levels
- **8 Focus Areas** - Conversation, Grammar, Vocabulary, Pronunciation, Writing, Reading, Listening, Culture
- **Adaptive Difficulty** - AI adjusts to your learning pace

### 🗣️ Full Communication Support
- **Speech Recognition** - Real-time voice input in 70+ languages
- **Text-to-Speech** - Native-quality pronunciation with multiple voices
- **Pronunciation Evaluation** - Phoneme-level scoring with visual feedback
- **Mixed Mode** - Seamlessly switch between typing and speaking

### 📚 Content Types
- **Dialogues** - Interactive conversations with native speakers
- **Exercises** - Multiple choice, fill-in-the-blank, translation, writing
- **Videos** - Subtitled content with transcripts
- **Audio** - Podcasts, dialogues, shadowing practice
- **Flashcards** - Spaced repetition (SM-2 algorithm)
- **Quizzes** - Timed assessments with detailed feedback
- **Reading** - Articles with vocabulary support
- **Writing** - AI-evaluated compositions with corrections

### 🤖 AI Tutor
- **Real-time Chat** - Practice conversation anytime
- **Grammar Correction** - Instant feedback on errors
- **Vocabulary Suggestions** - Contextual word recommendations
- **Personalized Lessons** - Adaptive content based on weaknesses
- **Roleplay Scenarios** - Restaurant, travel, business, medical

### 📊 Progress Tracking
- **Skill Radar** - Visual breakdown of 8 focus areas
- **Streak Tracking** - Daily practice motivation
- **XP & Levels** - Gamified progression
- **Achievements** - 50+ unlockable badges
- **Detailed Reports** - Weekly, monthly, yearly exports

### 🔧 Technical Features
- **Offline Support** - Download lessons for offline study
- **Cross-platform** - Web, iOS, Android (via Capacitor)
- **Real-time Sync** - Progress syncs across devices
- **WebSocket Chat** - Low-latency tutor communication
- **Export/Import** - Data portability (JSON, CSV, PDF)

## Tech Stack

### Backend
- **FastAPI** - Modern, fast Python web framework
- **SQLAlchemy 2.0** - Async ORM with SQLite/PostgreSQL
- **Pydantic v2** - Data validation and serialization
- **Redis** - Caching and session management
- **JWT** - Stateless authentication
- **Alembic** - Database migrations

### Frontend
- **React 18** - Modern UI library
- **TypeScript** - Type-safe development
- **Vite** - Lightning-fast build tool
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Smooth animations
- **Zustand** - Lightweight state management
- **React Router v6** - Client-side routing

### Speech & AI
- **Web Speech API** - Browser-native speech recognition/synthesis
- **OpenAI/Anthropic** - LLM integration for tutor responses
- **Canvas Confetti** - Celebration animations

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Redis (optional, for caching)

### Backend Setup
```bash
cd tutor-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd tutor-service/frontend
npm install
npm run dev
```

### Docker
```bash
cd tutor-service
docker-compose up -d
```

## Project Structure

```
tutor-service/
├── app/                    # Backend
│   ├── api/v1/            # API routes
│   │   ├── endpoints/     # Route handlers
│   │   └── router.py      # Main router
│   ├── core/              # Core configuration
│   │   ├── config.py      # Settings
│   │   └── database.py    # DB setup
│   ├── models/            # SQLAlchemy models
│   │   ├── user.py        # User & progress models
│   │   └── lesson.py      # Lesson & content models
│   ├── schemas/           # Pydantic schemas
│   │   ├── user.py        # User schemas
│   │   └── lesson.py      # Lesson schemas
│   ├── services/          # Business logic
│   └── main.py            # FastAPI app entry
├── frontend/              # Frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   │   ├── ui/        # Base UI components
│   │   │   ├── layout/    # Layout components
│   │   │   ├── lesson/    # Lesson players
│   │   │   ├── chat/      # Chat interface
│   │   │   ├── pronunciation/
│   │   │   └── writing/
│   │   ├── pages/         # Page components
│   │   ├── hooks/         # Custom hooks
│   │   ├── stores/        # Zustand stores
│   │   ├── contexts/      # React contexts
│   │   ├── lib/           # Utilities
│   │   └── types/         # TypeScript types
│   ├── package.json
│   └── vite.config.ts
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Get current user

### Users
- `GET /api/v1/users/me/progress` - Get progress
- `PUT /api/v1/users/me/progress` - Update progress
- `GET /api/v1/users/me/lessons/{id}/progress` - Lesson progress
- `GET /api/v1/users/me/achievements` - Achievements
- `GET /api/v1/users/me/practice-sessions` - Practice history
- `GET/PUT /api/v1/users/me/settings` - User settings

### Lessons
- `GET /api/v1/lessons/curriculum` - Full curriculum
- `GET /api/v1/lessons` - List lessons (with filters)
- `GET /api/v1/lessons/{id}` - Get lesson with progress
- `GET /api/v1/lessons/{id}/content/{content_id}` - Get content

### Practice
- `GET /api/v1/practice/modes` - Practice modes
- `GET /api/v1/practice/modes/{mode}/content` - Mode content
- `POST /api/v1/practice/exercise/submit` - Submit exercise
- `POST /api/v1/practice/pronunciation/evaluate` - Evaluate pronunciation
- `POST /api/v1/practice/writing/evaluate` - Evaluate writing

### Progress
- `GET /api/v1/progress/overview` - Progress overview
- `GET /api/v1/progress/skills` - Skill breakdown
- `GET /api/v1/progress/activity` - Activity heatmap
- `GET /api/v1/progress/achievements` - Achievements
- `GET /api/v1/progress/leaderboard` - Leaderboard
- `GET /api/v1/progress/report` - Generate report

### Vocabulary
- `GET /api/v1/vocabulary` - List vocabulary
- `GET /api/v1/vocabulary/stats` - Vocabulary stats
- `POST /api/v1/vocabulary` - Add word
- `POST /api/v1/vocabulary/{id}/review` - Review (SM-2)
- `GET /api/v1/vocabulary/export` - Export vocabulary

### Chat
- `GET /api/v1/chat/sessions` - Chat sessions
- `POST /api/v1/chat/sessions` - Create session
- `WS /api/v1/chat/ws/{user_id}` - Real-time chat

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./tutor.db` |
| `SECRET_KEY` | JWT secret (min 32 chars) | Required |
| `OPENAI_API_KEY` | OpenAI API key | Optional |
| `ANTHROPIC_API_KEY` | Anthropic API key | Optional |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `DEBUG` | Enable debug mode | `false` |

## Development

### Running Tests
```bash
# Backend
pytest app/tests/

# Frontend
cd frontend && npm test
```

### Code Quality
```bash
# Backend
ruff check app/
mypy app/

# Frontend
cd frontend && npm run lint
```

### Database Migrations
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Deployment

### Production Checklist
- [ ] Set strong `SECRET_KEY`
- [ ] Configure PostgreSQL database
- [ ] Set up Redis cluster
- [ ] Configure SSL/TLS
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure log aggregation
- [ ] Set up CI/CD pipeline
- [ ] Configure backup strategy

### Docker Production
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

Proprietary - All rights reserved.

## Support

- Documentation: https://docs.tutor.yourdomain.com
- Issues: https://github.com/yourorg/tutor-service/issues
- Email: support@tutor.yourdomain.com

---

Built with ❤️ for language learners worldwide.