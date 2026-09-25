FROM node:20-alpine

WORKDIR /app
COPY package.json ./
COPY server.js ./

ENV NODE_ENV=production
EXPOSE 4000

CMD ["node", "server.js"]