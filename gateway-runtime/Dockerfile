FROM node:22-alpine AS builder

WORKDIR /app
COPY package.json ./
RUN npm install --frozen-lockfile
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

# ── Runtime image ─────────────────────────────────────────────────────────────
FROM node:22-alpine

WORKDIR /app
RUN mkdir -p /data   # SQLite L2 storage

COPY package.json ./
RUN npm install --frozen-lockfile --omit=dev

COPY --from=builder /app/dist ./dist

ENV NODE_ENV=production

EXPOSE ${GATEWAY_PORT:-5000}

HEALTHCHECK --interval=5s --timeout=3s --retries=6 \
  CMD wget -qO- http://localhost:${GATEWAY_PORT:-5000}/internal/health || exit 1

CMD ["node", "dist/index.js"]
