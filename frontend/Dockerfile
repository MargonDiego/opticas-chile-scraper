# Multi-stage Dockerfile for Astro Frontend using Bun
FROM oven/bun:1-alpine AS builder

WORKDIR /app

COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile || bun install

COPY . .

# Astro bakes PUBLIC_* vars into the static bundle at build time via Vite -
# a runtime `environment:` entry in docker-compose is invisible to this
# `RUN bun run build` step, so these must arrive as build args instead.
ARG PUBLIC_API_URL
ARG PUBLIC_API_KEY
ENV PUBLIC_API_URL=$PUBLIC_API_URL
ENV PUBLIC_API_KEY=$PUBLIC_API_KEY

RUN bun run build

# Production static server (unrestricted Host headers for Cloudflare / Coolify tunnels)
FROM oven/bun:1-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3001

COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist

EXPOSE 3001

CMD ["bun", "run", "serve"]