FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 4200

CMD ["npx", "nx", "serve", "frontend", "--host", "0.0.0.0", "--port", "4200", "--disable-host-check"]
