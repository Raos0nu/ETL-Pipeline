# 🚀 Quick Start Guide - Modernized ETL Pipeline

## Option 1: Modernized App (Recommended)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env if needed (optional - defaults work for local dev)
# For production, set SECRET_KEY, DATABASE_URL, etc.
```

### 3. Run the Modernized App

```bash
python app_modern.py
```

The server will start on `http://localhost:5000`

## Option 2: Docker (Recommended for Production)

### 1. Build and Run

```bash
docker-compose up --build
```

### 2. Access the Dashboard

Open your browser to: `http://localhost:5000`

### 3. Stop the Container

```bash
docker-compose down
```

## Option 3: Legacy App (Backward Compatible)

If you need to use the original app:

```bash
python app.py
```

## Key Differences

### Modern App (`app_modern.py`)

- ✅ Configuration management (`.env` file)
- ✅ Structured logging (JSON or text)
- ✅ SQLAlchemy ORM (works with PostgreSQL, MySQL, etc.)
- ✅ Data validation with Pydantic
- ✅ Data quality checks
- ✅ Enhanced health checks
- ✅ Metrics endpoint
- ✅ Better error handling

### Legacy App (`app.py`)

- ✅ Simple, straightforward
- ✅ Works without additional setup
- ✅ Good for quick testing
- ⚠️ Less features

## Environment Variables

Create a `.env` file (or use `.env.example` as template):

```env
# Application
SECRET_KEY=your-secret-key-here
DEBUG=False
LOG_LEVEL=INFO
LOG_FORMAT=json

# Database
DATABASE_URL=sqlite:///sales.db

# ETL
DATA_FILE=data/sample_sales.csv
ENABLE_DATA_QUALITY_CHECKS=True

# CORS (for frontend)
CORS_ORIGINS=http://localhost:3000,http://localhost:5000
```

## Testing the API

### Health Check

```bash
curl http://localhost:5000/api/health
```

### Get Data

```bash
curl http://localhost:5000/api/data?page=1&per_page=10
```

### Run ETL Pipeline

```bash
curl -X POST http://localhost:5000/api/etl/run
```

### Metrics (Modern App Only)

```bash
curl http://localhost:5000/api/metrics
```

## Troubleshooting

### Import Errors

If you see import errors:
1. Make sure all dependencies are installed: `pip install -r requirements.txt`
2. The app will fall back to legacy mode automatically
3. Check that Python 3.11+ is being used

### Database Errors

1. Delete `sales.db` and restart (it will be recreated)
2. Check database permissions
3. For PostgreSQL, ensure connection string is correct

### Port Already in Use

Change the port in `.env`:
```env
PORT=5001
```

Or run with:
```bash
python app_modern.py --port 5001
```

## Next Steps

1. Review [MODERNIZATION_GUIDE.md](MODERNIZATION_GUIDE.md) for detailed information
2. Check [README.md](README.md) for full documentation
3. Explore the new features in the modernized app

## Need Help?

- Check the [MODERNIZATION_GUIDE.md](MODERNIZATION_GUIDE.md)
- Review error logs in `logs/etl_pipeline.log` (if configured)
- Check console output for detailed error messages
