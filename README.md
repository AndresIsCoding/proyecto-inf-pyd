# proyecto-inf-pyd

## Descripción

Proyecto desarrollado para la materia de Paralelas y Distribuidas. Incluye un backend en Node.js (con Docker Compose) y un frontend en React.

---

## Requisitos previos

- Docker
- Docker Compose
- Node.js 16 o superior (solo si deseas ejecutar el frontend localmente)
- npm
- Git

---

## Instalación

1. Clona el repositorio:
   ```sh
   git clone https://github.com/tu-usuario/proyecto-inf-pyd.git
   cd proyecto-inf-pyd
   ```

---

## Ejecución local

### Backend (Docker Compose)

1. Ve a la carpeta del backend (o donde esté el archivo `docker-compose.yml`):
   ```sh
   cd backend
   ```
2. Levanta los servicios:
   ```sh
   docker compose up -d
   ```
   Esto iniciará el backend y cualquier otro servicio definido en el archivo `docker-compose.yml`.

### Frontend

1. Abre una nueva terminal y ve a la carpeta del frontend:
   ```sh
   cd frontend
   npm install
   npm start
   ```

- El backend estará disponible en el puerto definido en tu `docker-compose.yml` (por ejemplo, `http://localhost:3001`).
- El frontend estará disponible en `http://localhost:3000`.

---

## Despliegue en AWS

### Backend (EC2 + Docker Compose)

1. **Lanza una instancia EC2** (Ubuntu recomendado) y abre el puerto del backend en el Security Group.
2. **Conéctate por SSH**:
   ```sh
   ssh -i tu-llave.pem ubuntu@<IP_PUBLICA>
   ```
3. **Instala Docker y Docker Compose**:
   ```sh
   sudo apt-get update
   sudo apt-get install -y docker.io
   sudo systemctl start docker
   sudo systemctl enable docker
   sudo usermod -aG docker $USER
   # Cierra y vuelve a abrir la sesión SSH para aplicar el grupo docker
   sudo apt-get install -y docker-compose
   ```
4. **Clona el repositorio y ve a la carpeta del backend**:
   ```sh
   git clone https://github.com/tu-usuario/proyecto-inf-pyd.git
   cd proyecto-inf-pyd/backend
   ```
5. **Levanta los servicios**:
   ```sh
   docker compose up -d
   ```

### Frontend

#### Opción 1: S3 + CloudFront

1. Construye el frontend:
   ```sh
   cd frontend
   npm install
   npm run build
   ```
2. Sube el contenido de la carpeta `build` a un bucket S3 configurado para hosting estático.
3. (Opcional) Configura CloudFront para distribución global.

#### Opción 2: EC2

1. Sigue los pasos de instalación en EC2.
2. Sirve el frontend con un servidor estático:
   ```sh
   npm install -g serve
   serve -s build
   ```
#### Benchmarking 

Instrucciones para realizar benchmarks comparatvos entre version secuencial y paralela

1. Configurar entorno (solo la primera vez)
python setup_benchmark.py

2. Ejecutar benchmark completo (10-15 min)
python run_benchmark.py

3. O ejecutar prueba rápida (2-3 min)
python run_benchmark.py --quick

4. Solo verificar que servicios estén listos
python run_benchmark.py --check
