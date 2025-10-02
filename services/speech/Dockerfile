FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias para Debian Trixie (nuevos nombres de paquetes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Crear directorio de almacenamiento
RUN mkdir -p ./app/storage

# Exponer el puerto
EXPOSE 8002

# Comando para ejecutar la aplicación
CMD ["python", "main.py"]