# ==================== STAGE 1: Builder ====================
FROM node:20-alpine as builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache libc6-compat

# Copy package files first for better layer caching
COPY package*.json ./

# Install dependencies with clean install
RUN npm ci --only=production=false && \
    npm cache clean --force

# Copy source code
COPY . .

# Build arguments for environment variables
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL:-http://localhost/api}

# Build the application
RUN npm run build && \
    rm -rf node_modules

# ==================== STAGE 2: Production ====================
FROM nginx:alpine

# Install wget for health checks
RUN apk add --no-cache wget && \
    rm -rf /var/cache/apk/*

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration (if exists)
COPY nginx.conf /etc/nginx/conf.d/default.conf 2>/dev/null || true

# Create nginx cache directories
RUN mkdir -p /var/cache/nginx/client_temp \
    /var/cache/nginx/proxy_temp \
    /var/cache/nginx/fastcgi_temp \
    /var/cache/nginx/uwsgi_temp \
    /var/cache/nginx/scgi_temp && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/log/nginx

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Expose port
EXPOSE 80

# Start nginx as non-root (nginx user already exists in alpine)
USER nginx

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
