# LoyalPay Deployment Guide

## Quick Deploy to Render (Free)

### Step 1: Push to GitHub

```bash
cd /Users/utkrsshh/personal/loyalpay
git init
git add .
git commit -m "Initial commit - LoyalPay"
gh repo create loyalpay --public --push
```

Or manually create a repo on GitHub and push.

### Step 2: Deploy on Render

1. Go to [render.com](https://render.com) and sign up/login
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub account
4. Select the `loyalpay` repository
5. Render will auto-detect `render.yaml` and create 3 services
6. Click **"Apply"** and wait ~5 minutes

### Step 3: Your Live URLs

After deployment, you'll get:
- **API**: `https://loyalpay-api.onrender.com`
- **Merchant App**: `https://loyalpay-merchant.onrender.com`
- **Customer App**: `https://loyalpay-customer.onrender.com`

---

## Manual Deploy (Individual Services)

### Backend (Python FastAPI)

1. Create new **Web Service** on Render
2. Connect GitHub repo
3. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.api:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3

### Merchant App (React)

1. Create new **Static Site** on Render
2. Connect GitHub repo
3. Settings:
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Publish Directory**: `frontend/dist`
4. Add Environment Variable:
   - `VITE_API_URL` = `https://your-api-url.onrender.com`

### Customer App (React)

1. Create new **Static Site** on Render
2. Connect GitHub repo
3. Settings:
   - **Build Command**: `cd customer-app && npm install && npm run build`
   - **Publish Directory**: `customer-app/dist`
4. Add Environment Variable:
   - `VITE_API_URL` = `https://your-api-url.onrender.com`

---

## Alternative: Railway

1. Go to [railway.app](https://railway.app)
2. Create new project from GitHub
3. Add 3 services pointing to the same repo
4. Configure each service's start command

---

## Local Development

```bash
# Backend
source venv/bin/activate
uvicorn backend.api:app --reload --port 8000

# Merchant App (new terminal)
cd frontend && npm run dev

# Customer App (new terminal)
cd customer-app && npm run dev
```

URLs:
- Backend: http://localhost:8000
- Merchant: http://localhost:5173
- Customer: http://localhost:5175
