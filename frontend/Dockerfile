# syntax=docker/dockerfile:1.7
# ---------- Stage 1: build the React bundle with Node ----------
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# ---------- Stage 2: serve static files with unprivileged Nginx ----------
# nginx-unprivileged runs as UID 101 and listens on 8080, so no root and no privileged port.
FROM nginxinc/nginx-unprivileged:1.29-alpine AS runtime

LABEL org.opencontainers.image.title="medislot-frontend" \
      org.opencontainers.image.description="MediSlot clinic dashboard (React + Nginx)" \
      org.opencontainers.image.source="https://github.com/ayushsingh199/DevOps_Capstone_Project"

USER root
RUN apk upgrade --no-cache && rm -f /etc/nginx/conf.d/default.conf
USER 101

ENV BACKEND_URL=http://backend:8000
COPY --chown=101:101 nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build --chown=101:101 /app/dist /usr/share/nginx/html

EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --retries=3 CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
