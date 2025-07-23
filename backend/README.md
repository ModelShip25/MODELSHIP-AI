# ModelShip Backend

ModelShip is an AI-powered auto-labeling platform for images and text. This repository contains the backend service built with FastAPI, YOLOX, and Supabase.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- [Supabase Account](https://supabase.com)
- [YOLOX ONNX Model](https://github.com/Megvii-BaseDetection/YOLOX)

### Setup

1. **Clone and Install**

```bash
# Clone repository
git clone <repository-url>
cd modelship/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

2. **Environment Configuration**

Create `.env` file in the backend directory:

```env
# App
APP_NAME=ModelShip
DEBUG=true
ENVIRONMENT=development

# Supabase
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key

# Storage
UPLOAD_DIR=uploads
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif

# ML Model
MODEL_PATH=models/yolox_s.onnx
CONFIDENCE_THRESHOLD=0.3
NMS_THRESHOLD=0.45
```

3. **Database Setup**

```bash
# Navigate to Supabase dashboard
# Run the SQL files in this order:
1. supabase/schema.sql
2. supabase/tables/users.sql
3. supabase/tables/images.sql
4. supabase/tables/annotations.sql
```

4. **Run the Server**

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/docs` for API documentation.

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py                     # FastAPI entrypoint
│   ├── core/
│   │   ├── config.py               # App configs
│   │   └── utils.py                # Shared helpers
│   ├── models/                     # Pydantic models
│   │   ├── image.py
│   │   ├── annotation.py
│   │   └── user.py
│   ├── services/                   # Business logic
│   │   ├── cleaning.py             # Deduplication
│   │   ├── labeling.py             # ML pipeline
│   │   ├── export.py               # Data export
│   │   └── preview.py              # Visualization
│   ├── pipeline/                   # ML components
│   │   ├── detector.py             # YOLOX model
│   │   ├── sahi_wrapper.py         # Image slicing
│   │   └── config.py               # ML settings
│   ├── routes/                     # API endpoints
│   │   ├── upload.py
│   │   ├── clean.py
│   │   ├── label.py
│   │   ├── preview.py
│   │   └── export.py
│   └── storage/                    # Storage logic
│       ├── image_store.py
│       └── label_store.py
├── supabase/                       # Database
│   ├── schema.sql
│   └── tables/
│       ├── users.sql
│       ├── images.sql
│       └── annotations.sql
├── models/                         # ML models
├── uploads/                        # Local storage
└── requirements.txt
```

## 🔄 Development Workflow

### Phase 1: Environment Setup
- [x] Project structure
- [x] Dependencies
- [x] Configuration
- [x] Database schema

### Phase 2: Storage Layer
- [x] Image store service
- [x] Label store service
- [x] Supabase integration
- [x] File validation

### Phase 3: ML Pipeline
- [ ] YOLOX model integration
- [ ] SAHI wrapper
- [ ] Prediction pipeline
- [ ] Error handling

### Phase 4: Core Services
- [ ] Image cleaning
- [ ] Auto-labeling
- [ ] Preview generation
- [ ] Export formats

### Phase 5: API Routes
- [ ] Upload endpoint
- [ ] Processing endpoint
- [ ] Export endpoint
- [ ] Status tracking

### Phase 6: Testing & Polish
- [ ] Unit tests
- [ ] Integration tests
- [ ] Documentation
- [ ] Performance optimization

## 🛠 API Endpoints

### Upload
```
POST /api/upload
- Upload single/multiple images
- Returns image IDs and metadata
```

### Processing
```
POST /api/process/{image_id}
- Run ML pipeline on image
- Returns annotations
```

### Export
```
POST /api/export
- Export annotations in various formats
- Supports YOLO, COCO, CSV
```

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## 📦 Deployment

### Railway (Recommended)
1. Connect GitHub repository
2. Set environment variables
3. Deploy

### Docker
```bash
# Build image
docker build -t modelship-backend .

# Run container
docker run -p 8000:8000 modelship-backend
```

## 🔒 Security

- All endpoints require authentication
- Row Level Security in Supabase
- File validation and sanitization
- Rate limiting on API routes

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Supabase Documentation](https://supabase.io/docs)
- [YOLOX Repository](https://github.com/Megvii-BaseDetection/YOLOX)
- [SAHI Documentation](https://github.com/obss/sahi)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open pull request

## 📝 License

MIT License - see LICENSE file for details
