# Stage 1 – build
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2 – serve with nginx
FROM nginx:stable-alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html

# Proxy /api calls to the backend container
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
