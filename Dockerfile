# ÉTAPE 1 : Compilation de Tailwind CSS

FROM node:24-alpine AS tailwind-builder

WORKDIR /app

# Copier les fichiers nécessaires à Tailwind
COPY package*.json ./

# Installer les dépendances Node.js
RUN npm install

# Copier le reste du projet
COPY . .

# Compiler Tailwind CSS
RUN npx tailwindcss \
    -i ./tailwind.input.css \
    -o ./app/static/css/tailwind.css \
    --minify


    
# ÉTAPE 2 : Application FastAPI

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copier requirements.txt
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le projet
COPY . .

# Copier le CSS Tailwind compilé depuis l'étape Node
COPY --from=tailwind-builder /app/app/static/css/tailwind.css ./app/static/css/tailwind.css

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]