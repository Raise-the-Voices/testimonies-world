# syntax=docker/dockerfile:1.7
#
# Multi-stage build for the SvelteKit frontend.
#
#   builder  — node:22-alpine; takes PUBLIC_BASE_PATH as an ARG
#              (svelte.config.js reads it at config time, so it
#              must be set before 'npm run build'); runs the full
#              build including the adapter-node compile.
#   runtime  — node:22-alpine; copies build/ + package.json +
#              node_modules; applies the deploy.sh:115-117
#              symlink trick via the entrypoint --link-only
#              step at build time; runs 'node build/index.js'.
#
# orval is a devDep that runs at 'gen:api' time, not at
# 'build' time — the production npm run build is just vite
# build. The orval-generated files are committed to
# frontend/src/lib/api/generated/ and pulled into the image
# via COPY . .. so no API generation is needed in the image.

# ---------- builder ----------
FROM node:22-alpine AS builder
WORKDIR /app

# PUBLIC_BASE_PATH is read by svelte.config.js at config time
# (and by vite for asset paths), so it must be set before the
# 'npm run build' call. Build arg → env so child processes
# inherit it.
ARG PUBLIC_BASE_PATH=/testimonies
ENV PUBLIC_BASE_PATH=$PUBLIC_BASE_PATH

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# ---------- runtime ----------
FROM node:22-alpine AS runtime
WORKDIR /app

# wget for the HEALTHCHECK (no curl in alpine by default; the
# build stage already has busybox tools but the runtime image
# is stripped).
RUN apk add --no-cache wget

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000

# Copy build artifacts + the node_modules (the runtime needs
# the SvelteKit chunks and any runtime deps not inlined by
# adapter-node). package.json is needed for the version field
# in adapter-node's startup banner.
COPY --from=builder /app/build /app/build
COPY --from=builder /app/package.json /app/package.json
COPY --from=builder /app/node_modules /app/node_modules

# Preserve the deploy.sh:115-117 symlink trick. The runtime
# image re-applies the symlink at start (scripts/docker/
# entrypoint-frontend.sh), but we also apply it at build
# time so the image's working state matches what deploy.sh
# produces on the host.
RUN scripts/docker/entrypoint-frontend.sh --link-only

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -qO- http://localhost:3000/ >/dev/null || exit 1

ENTRYPOINT ["scripts/docker/entrypoint-frontend.sh"]
CMD ["node", "build/index.js"]
