# Combined Dockerfile - Backend + Both Frontends
# Single service deployment for Koyeb free tier

# Stage 1: Build Merchant Frontend
FROM node:18-alpine AS merchant-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build Customer Frontend
FROM node:18-alpine AS customer-build
WORKDIR /app/customer-app
COPY customer-app/package*.json ./
RUN npm install
COPY customer-app/ ./
RUN npm run build

# Stage 3: Python Backend + Static Files
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontends
COPY --from=merchant-build /app/frontend/dist ./static/merchant
COPY --from=customer-build /app/customer-app/dist ./static/customer

# Expose port
EXPOSE 8000

# Start server
CMD uvicorn backend.api:app --host 0.0.0.0 --port ${PORT:-8000}
