# Despliegue en Google Cloud Platform (GCP) / Firebase

## 🔍 Firebase vs Google Cloud Platform

**Firebase** es parte de **Google Cloud Platform (GCP)**, pero tienen diferentes servicios:

### Firebase (No puede ejecutar Docker Compose)
- ✅ **Firebase Hosting**: Solo para archivos estáticos (HTML, CSS, JS)
- ✅ **Firebase Functions**: Funciones serverless (Node.js, Python)
- ❌ **No puede ejecutar Docker Compose directamente**

### Google Cloud Platform (SÍ puede ejecutar Docker Compose)
- ✅ **Compute Engine (GCE)**: VPS equivalente, puede ejecutar Docker Compose
- ✅ **Cloud Run**: Serverless con contenedores (pero no Docker Compose)
- ✅ **GKE**: Kubernetes (más complejo)

## 🎯 Opción Recomendada: Compute Engine (GCE)

**Google Compute Engine** es el equivalente a un VPS en GCP. Puedes:
- Instalar Docker y Docker Compose
- Ejecutar tu aplicación exactamente igual que en DigitalOcean/Hetzner
- Integrarlo con Firebase Hosting para el frontend (opcional)

---

## 📋 Guía de Despliegue: GCP Compute Engine

### Paso 1: Crear Proyecto en Google Cloud

1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Crear nuevo proyecto o seleccionar existente
3. Habilitar facturación (necesario para Compute Engine)

### Paso 2: Crear Instancia de Compute Engine

```bash
# Opción A: Desde la consola web
# 1. Ir a Compute Engine > VM instances
# 2. Click "Create Instance"
# 3. Configuración recomendada:
#    - Name: nba-live-api
#    - Region: us-central1 (o la más cercana a ti)
#    - Machine type: e2-small (2 vCPU, 2GB RAM) - $15/mes
#    - Boot disk: Ubuntu 22.04 LTS, 20GB
#    - Firewall: Allow HTTP traffic, Allow HTTPS traffic
# 4. Click "Create"

# Opción B: Desde gcloud CLI
gcloud compute instances create nba-live-api \
  --zone=us-central1-a \
  --machine-type=e2-small \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB \
  --tags=http-server,https-server
```

### Paso 3: Configurar Firewall

```bash
# Permitir tráfico HTTP y HTTPS
gcloud compute firewall-rules create allow-http \
  --allow tcp:80 \
  --source-ranges 0.0.0.0/0 \
  --target-tags http-server

gcloud compute firewall-rules create allow-https \
  --allow tcp:443 \
  --source-ranges 0.0.0.0/0 \
  --target-tags https-server
```

### Paso 4: Conectar a la Instancia

```bash
# Obtener IP externa
gcloud compute instances describe nba-live-api --zone=us-central1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# Conectar por SSH
gcloud compute ssh nba-live-api --zone=us-central1-a

# O usar SSH tradicional
ssh usuario@IP_EXTERNA
```

### Paso 5: Configurar Servidor (igual que VPS tradicional)

```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Instalar Docker Compose
apt install docker-compose-plugin -y

# Instalar Nginx
apt update && apt install nginx certbot python3-certbot-nginx -y

# Configurar firewall (GCP ya maneja esto, pero por seguridad local)
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw enable
```

### Paso 6: Desplegar Aplicación

```bash
# Clonar repositorio
mkdir -p /opt/nba-live && cd /opt/nba-live
git clone tu-repo.git .

# Crear .env
nano .env

# Desplegar
./scripts/deploy.sh
```

### Paso 7: Configurar Nginx y SSL

Igual que en la guía de VPS tradicional. Usar el template de `nginx/nba-live.conf`.

---

## 🔄 Integración con Firebase Hosting (Opcional)

Si quieres usar **Firebase Hosting para el frontend** y **GCE para el backend**:

### Arquitectura Híbrida:
- **Frontend (Static)**: Firebase Hosting (gratis, CDN global)
- **Backend API**: Compute Engine (Docker Compose)

### Configuración:

1. **Desplegar Frontend en Firebase Hosting**:
```bash
# Instalar Firebase CLI
npm install -g firebase-tools

# Inicializar proyecto
firebase init hosting

# Configurar firebase.json
```

**firebase.json**:
```json
{
  "hosting": {
    "public": "static",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "/api/**",
        "destination": "https://tu-dominio-api.com/api/**"
      },
      {
        "source": "**",
        "destination": "/index.html"
      }
    ],
    "headers": [
      {
        "source": "**/*.@(js|css)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "max-age=31536000"
          }
        ]
      }
    ]
  }
}
```

2. **Configurar CORS en tu API** (si es necesario):
```python
# En tu Flask app
from flask_cors import CORS

CORS(app, resources={
    r"/*": {
        "origins": [
            "https://tu-proyecto.web.app",
            "https://tu-proyecto.firebaseapp.com",
            "https://tu-dominio.com"
        ]
    }
})
```

3. **Desplegar**:
```bash
firebase deploy --only hosting
```

---

## 💰 Costos de GCP Compute Engine

### Instancias Recomendadas:

| Tipo | vCPU | RAM | Costo/mes | Uso |
|------|------|-----|-----------|-----|
| **e2-small** | 2 | 2GB | ~$15 | Desarrollo/Pequeño |
| **e2-medium** | 2 | 4GB | ~$30 | Producción pequeña |
| **e2-standard-2** | 2 | 8GB | ~$50 | Producción media |

### Costos Adicionales:
- **Tráfico de red**: Primeros 1GB gratis, luego $0.12/GB
- **Almacenamiento**: $0.17/GB/mes (20GB = ~$3.40/mes)
- **IP estática**: Gratis si está en uso

### Total Estimado:
- **Mínimo**: ~$18-20/mes (e2-small + storage)
- **Recomendado**: ~$35-40/mes (e2-medium + storage)

---

## 🆚 Comparación: GCP vs Otros VPS

| Característica | GCP Compute Engine | DigitalOcean | Hetzner |
|----------------|-------------------|--------------|---------|
| **Costo/mes** | $15-30 | $12-24 | €4-8 |
| **Integración Firebase** | ✅ Nativa | ❌ | ❌ |
| **Curva aprendizaje** | Media | Baja | Baja |
| **Documentación** | Excelente | Buena | Buena |
| **Créditos gratis** | $300 por 90 días | $200 por 60 días | No |

---

## 🎯 ¿Cuándo Usar GCP vs Otros VPS?

### Usa GCP Compute Engine si:
- ✅ Ya usas Firebase para otras cosas
- ✅ Quieres integración con otros servicios de GCP
- ✅ Necesitas integración con Google Cloud SQL (opcional)
- ✅ Tienes créditos gratis de GCP
- ✅ Prefieres el ecosistema Google

### Usa DigitalOcean/Hetzner si:
- ✅ Solo necesitas un VPS simple
- ✅ Quieres el menor costo posible
- ✅ No necesitas integración con servicios de Google
- ✅ Prefieres simplicidad

---

## 📋 Checklist de Despliegue en GCP

- [ ] Crear proyecto en Google Cloud Console
- [ ] Habilitar facturación
- [ ] Crear instancia Compute Engine
- [ ] Configurar firewall (HTTP/HTTPS)
- [ ] Conectar por SSH
- [ ] Instalar Docker y Docker Compose
- [ ] Instalar Nginx y Certbot
- [ ] Clonar repositorio
- [ ] Configurar .env
- [ ] Configurar Nginx
- [ ] Obtener SSL (Let's Encrypt)
- [ ] Desplegar aplicación
- [ ] (Opcional) Configurar Firebase Hosting para frontend
- [ ] Probar endpoints
- [ ] Configurar backups

---

## 🚀 Comandos Útiles de GCP

```bash
# Ver instancias
gcloud compute instances list

# Iniciar instancia
gcloud compute instances start nba-live-api --zone=us-central1-a

# Detener instancia
gcloud compute instances stop nba-live-api --zone=us-central1-a

# Ver IP externa
gcloud compute instances describe nba-live-api --zone=us-central1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# Conectar por SSH
gcloud compute ssh nba-live-api --zone=us-central1-a

# Ver logs de la instancia
gcloud compute instances get-serial-port-output nba-live-api --zone=us-central1-a
```

---

## 🔐 Seguridad en GCP

1. **Firewall**: Configurar en GCP Console (no solo UFW local)
2. **SSH Keys**: GCP maneja esto automáticamente
3. **IP Estática**: Reservar una IP estática si necesitas
4. **Backups**: Usar snapshots de disco de GCP

---

## 📚 Recursos

- [GCP Compute Engine Docs](https://cloud.google.com/compute/docs)
- [Firebase Hosting Docs](https://firebase.google.com/docs/hosting)
- [GCP Pricing Calculator](https://cloud.google.com/products/calculator)
- [GCP Free Tier](https://cloud.google.com/free)

---

## ✅ Resumen

**Respuesta corta**: Firebase Hosting NO puede ejecutar Docker Compose, pero **Google Compute Engine (GCE) SÍ puede**, y está en el mismo ecosistema.

**Recomendación**:
- Si ya usas Firebase: Usa **GCE para el backend** + **Firebase Hosting para el frontend**
- Si no usas Firebase: **DigitalOcean o Hetzner son más económicos** ($12 vs $18-20/mes)

El proceso es **exactamente igual** que en cualquier VPS, solo cambia el proveedor.
