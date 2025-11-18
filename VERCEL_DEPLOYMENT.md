# 🚀 Vercel Deployment Guide

This guide will help you deploy your ETL Pipeline Dashboard to Vercel.

## 📋 Prerequisites

1. GitHub account with your repository
2. Vercel account (free tier works)
3. Your code pushed to GitHub

## 🔧 Deployment Steps

### Method 1: Deploy via Vercel Dashboard (Recommended)

1. **Go to Vercel**: Visit [vercel.com](https://vercel.com) and sign in
2. **Import Project**: Click "Add New" → "Project"
3. **Import Git Repository**: Select your GitHub repository
   - Repository: `Raos0nu/Data-Engineering-ETL-Pipeline`
4. **Configure Project**:
   - Framework Preset: **Other**
   - Root Directory: `./` (root)
   - Build Command: Leave empty (Vercel will auto-detect)
   - Output Directory: `frontend/build`
5. **Environment Variables**: None needed for basic setup
6. **Deploy**: Click "Deploy"

### Method 2: Deploy via Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy
vercel

# For production
vercel --prod
```

## ⚙️ Configuration Files

The project includes:

- **`vercel.json`** - Vercel configuration
- **`api/index.py`** - Serverless function for Flask API
- **`.vercelignore`** - Files to exclude from deployment

## 🔍 Important Notes

### File Structure for Vercel

```
your-repo/
├── api/
│   └── index.py          # Flask API serverless function
├── frontend/
│   ├── package.json
│   └── build/            # Built React app
├── data/
│   └── sample_sales.csv  # Data file
├── vercel.json           # Vercel config
└── requirements.txt      # Python dependencies
```

### API Routes

All API routes are prefixed with `/api/`:
- `/api/health` - Health check
- `/api/data` - Get/add sales data
- `/api/etl/run` - Run ETL pipeline
- `/api/analytics/products` - Product analytics

### Frontend Routes

All other routes serve the React app:
- `/` - Dashboard
- `/dashboard` - Dashboard (same as `/`)
- Any other route - Serves `index.html` for React Router

## 🐛 Troubleshooting

### Issue: "Not Found" Error

**Solution**: Make sure:
1. `vercel.json` is in the root directory
2. `api/index.py` exists and is properly configured
3. Frontend is built (`npm run build` in frontend directory)

### Issue: API Routes Not Working

**Solution**: 
1. Check that `api/index.py` is properly formatted
2. Verify routes start with `/api/`
3. Check Vercel function logs in dashboard

### Issue: Frontend Not Loading

**Solution**:
1. Ensure `frontend/build` directory exists
2. Run `cd frontend && npm run build`
3. Check `vercel.json` routes configuration

### Issue: Database Errors

**Note**: SQLite on Vercel has limitations (read-only filesystem in some cases).
For production, consider using:
- Vercel Postgres
- MongoDB Atlas
- Supabase
- Other cloud databases

## 📝 Environment Variables (Optional)

If you need environment variables:

1. Go to Vercel Dashboard
2. Select your project
3. Go to Settings → Environment Variables
4. Add variables as needed

## 🔄 Updating Deployment

After pushing to GitHub:

1. Vercel will auto-deploy if connected
2. Or manually trigger: Vercel Dashboard → Deployments → Redeploy

## 📊 Monitoring

- **Logs**: Vercel Dashboard → Your Project → Logs
- **Analytics**: Vercel Dashboard → Analytics
- **Functions**: Vercel Dashboard → Functions

## 🎉 Success!

Once deployed, your dashboard will be available at:
- `https://your-project-name.vercel.app`

---

**Need Help?** Check Vercel documentation: [vercel.com/docs](https://vercel.com/docs)

