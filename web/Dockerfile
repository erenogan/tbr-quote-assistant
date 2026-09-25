# 1. aşama: uygulamayı Node ile derle
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Tarayıcı backend'e bilgisayarın portundan ulaşır (Docker ağının içinden değil).
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# 2. aşama: sadece derlenmiş statik dosyaları küçük bir web sunucusuyla yayınla
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
