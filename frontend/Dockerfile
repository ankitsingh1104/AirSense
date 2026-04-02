FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Build Vite app
# RUN npm run build

# Expose Vite dev port
EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
