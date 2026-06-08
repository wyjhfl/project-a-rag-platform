ARG NODE_IMAGE=node:20-alpine
ARG NGINX_IMAGE=nginx:1.27-alpine

FROM ${NODE_IMAGE} AS build

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend ./

ARG VITE_API_BASE=http://127.0.0.1:18081
ENV VITE_API_BASE=$VITE_API_BASE

RUN npm run build

FROM ${NGINX_IMAGE}

COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80
