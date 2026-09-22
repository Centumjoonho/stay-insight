# Build from the repository root to include the pnpm workspace and lockfile.
FROM node:24-bookworm-slim
RUN npm install --global pnpm@11.19.0
WORKDIR /workspace
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY frontend/package.json ./frontend/package.json
RUN pnpm install --frozen-lockfile
COPY frontend ./frontend
WORKDIR /workspace/frontend
EXPOSE 3000
CMD ["pnpm", "dev"]
