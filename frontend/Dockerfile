FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Set the API URL to point to your backend
# Overriden in .env.production if present
ENV VITE_API_URL=https://api.explainerchonk.com 
RUN npm run build
# Keep container running so the volume persists
CMD ["tail", "-f", "/dev/null"]