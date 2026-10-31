# Deploy LoyalPay on Koyeb (All-in-One - Free Tier)

Everything runs on a single Koyeb service - Backend API + Both Frontend Apps!

---

## Your URLs After Deployment:

| App | URL |
|-----|-----|
| **Merchant App** | `https://your-app.koyeb.app/merchant` |
| **Customer App** | `https://your-app.koyeb.app/customer` |
| **API** | `https://your-app.koyeb.app/` |

---

## Step 1: Push Code to GitHub

```bash
cd /Users/utkrsshh/personal/loyalpay
git add .
git commit -m "LoyalPay - combined deployment"

# Create a new repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/loyalpay.git
git branch -M main
git push -u origin main
```

---

## Step 2: Deploy on Koyeb

1. Go to [koyeb.com](https://www.koyeb.com/) → **Sign up** (free)

2. Click **"Create App"**

3. Select **"GitHub"** as source

4. Connect your GitHub account & select **loyalpay** repo

5. Configure the service:
   - **Builder**: `Dockerfile`
   - **Dockerfile path**: `Dockerfile`
   - **Port**: `8000`
   - **Instance type**: `free`
   - **Region**: Choose closest (e.g., Frankfurt)

6. Click **"Deploy"**

7. Wait 3-5 minutes for build to complete

---

## Step 3: Access Your Apps! 🎉

Once deployed, you'll get a URL like: `https://loyalpay-xxxxx.koyeb.app`

- **Merchant App**: `https://loyalpay-xxxxx.koyeb.app/merchant`
- **Customer App**: `https://loyalpay-xxxxx.koyeb.app/customer`
- **API Health Check**: `https://loyalpay-xxxxx.koyeb.app/health`

---

## How It Works

The Dockerfile builds everything into one container:
1. Builds Merchant React app → `/static/merchant`
2. Builds Customer React app → `/static/customer`
3. Runs FastAPI backend that serves both static apps + API

```
https://your-app.koyeb.app/
├── /merchant      → Merchant React App
├── /customer      → Customer React App
├── /health        → API health check
├── /customers     → API endpoint
├── /at-risk       → API endpoint
└── ...            → All other API routes
```

---

## Troubleshooting

**Build fails?**
- Check logs in Koyeb dashboard
- Make sure all files are committed to GitHub

**Apps not loading?**
- Wait for build to complete (check Koyeb logs)
- Try hard refresh (Ctrl+Shift+R)

**API errors?**
- Check `/health` endpoint first
- Look at Koyeb runtime logs

---

## Local Testing (Combined Build)

```bash
# Build the Docker image locally
docker build -t loyalpay .

# Run it
docker run -p 8000:8000 loyalpay

# Access:
# http://localhost:8000/merchant
# http://localhost:8000/customer
```
