FROM node:20-alpine

WORKDIR /app

# Copie des fichiers de dépendances
COPY package*.json ./
RUN npm install

# Copie du reste du code source
COPY . .

EXPOSE 5173

# Lancement du serveur de dev Vite en écoutant sur toutes les interfaces (0.0.0.0)
CMD ["npm", "run", "dev", "--", "--host"]