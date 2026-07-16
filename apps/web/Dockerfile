FROM node:20-alpine AS base
WORKDIR /app
COPY package*.json ./
COPY apps/web/package.json apps/web/package.json
RUN npm install
COPY . .
WORKDIR /app/apps/web
RUN npm run build
RUN cp -r .next/static .next/standalone/apps/web/.next/static
EXPOSE 3000
CMD ["node", ".next/standalone/apps/web/server.js"]
