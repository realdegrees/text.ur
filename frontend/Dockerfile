FROM node:20-alpine AS builder
WORKDIR /app

# Install pnpm globally
RUN npm install -g pnpm

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Copy svelte config early to avoid prepare script warnings
COPY svelte.config.js ./
COPY vite.config.ts ./
COPY tsconfig.json ./

# Install dependencies with cache mount for faster rebuilds
RUN --mount=type=cache,id=pnpm,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

# Copy rest of application
COPY . .

# Build with cache mount
RUN --mount=type=cache,id=pnpm,target=/root/.local/share/pnpm/store \
    pnpm build

FROM node:20-alpine AS dependencies
WORKDIR /app

# Install pnpm globally
RUN npm install -g pnpm

# Copy package files and configs
COPY package.json pnpm-lock.yaml ./
COPY svelte.config.js ./
COPY vite.config.ts ./
COPY tsconfig.json ./

# Install production dependencies with cache mount
RUN --mount=type=cache,id=pnpm,target=/root/.local/share/pnpm/store \
    pnpm install --prod --frozen-lockfile

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/build ./build
COPY --from=dependencies /app/node_modules ./node_modules
COPY --from=dependencies /app/package.json ./
COPY --from=dependencies /app/pnpm-lock.yaml ./

EXPOSE 3000

CMD ["node", "build"]