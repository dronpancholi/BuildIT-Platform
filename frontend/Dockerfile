# ============================================================================
# SEO Operations Platform — Frontend Dockerfile
# ============================================================================
# Multi-stage build: installs deps, builds, then serves via standalone server.
# ============================================================================

# --- Stage 1: Dependencies ---
FROM node:22-alpine AS deps

RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm@10.28.2 && pnpm install --frozen-lockfile

# --- Stage 2: Builder ---
FROM node:22-alpine AS builder

RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

RUN npm install -g pnpm@10.28.2 && pnpm build

# --- Stage 3: Runner ---
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
