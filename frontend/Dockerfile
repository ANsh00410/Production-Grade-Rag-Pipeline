# ── Stage 1: build ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Declare build arg so docker-compose can pass VITE_API_URL in
ARG VITE_API_URL=/api
# Expose it as an env var so Vite bakes it into the bundle at build time
ENV VITE_API_URL=$VITE_API_URL

COPY package*.json ./
RUN npm ci --silent

COPY . .
RUN npm run build
# Output lands in /app/dist

# ── Stage 2: serve with Nginx ────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Remove default Nginx page
RUN rm -rf /usr/share/nginx/html/*

# Copy built React app
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy our Nginx config (handles SPA routing + API proxy)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
