# Despliegue en Microsoft Azure

## ✅ Sí, es Posible con Azure

Azure tiene varias opciones para desplegar Docker Compose, similar a GCP y otros proveedores.

---

## 🎯 Opción Recomendada: Azure Virtual Machines (VM)

**Azure Virtual Machines** es el equivalente a un VPS tradicional. Puedes:
- Instalar Docker y Docker Compose
- Ejecutar tu aplicación exactamente igual que en DigitalOcean/Hetzner/GCP
- Usar Azure App Service para el frontend (opcional)

---

## 📋 Guía de Despliegue: Azure Virtual Machine

### Paso 1: Crear Cuenta y Recursos en Azure

1. Ir a [Azure Portal](https://portal.azure.com/)
2. Crear cuenta gratuita (incluye $200 de crédito por 30 días)
3. Crear un nuevo **Resource Group** (grupo de recursos)

### Paso 2: Crear Virtual Machine

#### Opción A: Desde Azure Portal (Recomendado para empezar)

1. Ir a **Virtual machines** > **Create** > **Azure virtual machine**
2. Configuración recomendada:
   - **Subscription**: Tu suscripción
   - **Resource Group**: Crear nuevo o usar existente
   - **VM name**: `nba-live-api`
   - **Region**: `East US` o la más cercana a ti
   - **Image**: `Ubuntu Server 22.04 LTS`
   - **Size**: `Standard_B1s` (1 vCPU, 1GB RAM) - ~$7/mes
     - O `Standard_B2s` (2 vCPU, 4GB RAM) - ~$15/mes (recomendado)
   - **Authentication type**: SSH public key (más seguro) o Password
   - **Public inbound ports**: Allow selected ports > SSH (22), HTTP (80), HTTPS (443)
3. Click **Review + create** > **Create**

#### Opción B: Desde Azure CLI

```bash
# Instalar Azure CLI (si no lo tienes)
# macOS: brew install azure-cli
# Linux: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login

# Crear Resource Group
az group create --name nba-live-rg --location eastus

# Crear Virtual Machine
az vm create \
  --resource-group nba-live-rg \
  --name nba-live-api \
  --image Ubuntu2204 \
  --size Standard_B2s \
  --admin-username azureuser \
  --generate-ssh-keys \
  --public-ip-sku Standard \
  --nsg-rule SSH,HTTP,HTTPS
```

### Paso 3: Configurar Network Security Group (Firewall)

Azure crea automáticamente reglas de firewall, pero verifica:

1. Ir a **Network security groups** > Tu NSG
2. Verificar que existen reglas para:
   - **SSH (22)**: Allow
   - **HTTP (80)**: Allow
   - **HTTPS (443)**: Allow

O desde CLI:
```bash
# Agregar reglas de firewall
az network nsg rule create \
  --resource-group nba-live-rg \
  --nsg-name nba-live-api-nsg \
  --name AllowHTTP \
  --priority 1000 \
  --access Allow \
  --protocol Tcp \
  --direction Inbound \
  --source-port-ranges '*' \
  --destination-port-ranges 80

az network nsg rule create \
  --resource-group nba-live-rg \
  --nsg-name nba-live-api-nsg \
  --name AllowHTTPS \
  --priority 1001 \
  --access Allow \
  --protocol Tcp \
  --direction Inbound \
  --source-port-ranges '*' \
  --destination-port-ranges 443
```

### Paso 4: Conectar a la VM

```bash
# Obtener IP pública
az vm show -d -g nba-live-rg -n nba-live-api --query publicIps -o tsv

# Conectar por SSH
ssh azureuser@IP_PUBLICA

# O desde Azure Portal: Click en VM > Connect > SSH
```

### Paso 5: Configurar Servidor (igual que VPS tradicional)

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar usuario a grupo docker
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo apt install docker-compose-plugin -y

# Instalar Nginx
sudo apt install nginx certbot python3-certbot-nginx -y

# Configurar firewall local (Azure ya maneja esto, pero por seguridad)
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw enable
```

### Paso 6: Desplegar Aplicación

```bash
# Clonar repositorio
sudo mkdir -p /opt/nba-live && cd /opt/nba-live
sudo git clone tu-repo.git .
sudo chown -R $USER:$USER /opt/nba-live
cd /opt/nba-live

# Crear .env
nano .env

# Desplegar
./scripts/deploy.sh
```

### Paso 7: Configurar Nginx y SSL

Igual que en la guía de VPS tradicional. Usar el template de `nginx/nba-live.conf`.

---

## 🔄 Integración con Azure App Service (Opcional)

Si quieres usar **Azure App Service para el frontend** y **VM para el backend**:

### Arquitectura Híbrida:
- **Frontend (Static)**: Azure Static Web Apps (gratis) o App Service
- **Backend API**: Azure Virtual Machine (Docker Compose)

### Configuración Azure Static Web Apps:

1. **Crear Static Web App**:
```bash
# Instalar Azure Static Web Apps CLI
npm install -g @azure/static-web-apps-cli

# Inicializar
swa init

# Desplegar
swa deploy
```

2. **Configurar rewrites** en `staticwebapp.config.json`:
```json
{
  "routes": [
    {
      "route": "/api/*",
      "allowedRoles": ["anonymous"],
      "rewrite": "https://tu-dominio-api.com/api/*"
    }
  ],
  "navigationFallback": {
    "rewrite": "/index.html"
  }
}
```

---

## 💰 Costos de Azure Virtual Machines

### Tamaños Recomendados:

| Tamaño | vCPU | RAM | Costo/mes | Uso |
|--------|------|-----|-----------|-----|
| **Standard_B1s** | 1 | 1GB | ~$7 | Desarrollo/Testing |
| **Standard_B2s** | 2 | 4GB | ~$15 | Producción pequeña |
| **Standard_B2ms** | 2 | 8GB | ~$30 | Producción media |

### Costos Adicionales:
- **Storage (Disco)**: $0.10/GB/mes (30GB = ~$3/mes)
- **IP Pública**: Gratis si está en uso
- **Tráfico de red**: Primeros 5GB gratis, luego $0.05-0.08/GB

### Total Estimado:
- **Mínimo**: ~$10-12/mes (B1s + storage)
- **Recomendado**: ~$18-20/mes (B2s + storage)

### 💡 Créditos Gratis:
- **$200 de crédito** por 30 días (cuenta nueva)
- **12 meses gratis** de servicios populares
- **Siempre gratis**: Algunos servicios básicos

---

## 🆚 Comparación: Azure vs Otros Proveedores

| Característica | Azure VM | GCP Compute | DigitalOcean | Hetzner |
|----------------|----------|-------------|--------------|---------|
| **Costo/mes** | $15-20 | $15-30 | $12-24 | €4-8 |
| **Créditos gratis** | $200/30 días | $300/90 días | $200/60 días | No |
| **Integración Microsoft** | ✅ Nativa | ❌ | ❌ | ❌ |
| **Curva aprendizaje** | Media | Media | Baja | Baja |
| **Documentación** | Excelente | Excelente | Buena | Buena |
| **Soporte** | Excelente | Bueno | Bueno | Bueno |

---

## 🎯 ¿Cuándo Usar Azure vs Otros?

### Usa Azure Virtual Machines si:
- ✅ Ya usas servicios de Microsoft (Office 365, etc.)
- ✅ Necesitas integración con Azure Active Directory
- ✅ Quieres usar Azure SQL Database (opcional)
- ✅ Tienes créditos gratis de Azure
- ✅ Prefieres el ecosistema Microsoft
- ✅ Necesitas cumplir con compliance específico (Azure tiene muchas certificaciones)

### Usa DigitalOcean/Hetzner si:
- ✅ Solo necesitas un VPS simple
- ✅ Quieres el menor costo posible
- ✅ No necesitas integración con servicios de Microsoft
- ✅ Prefieres simplicidad

---

## 📋 Checklist de Despliegue en Azure

- [ ] Crear cuenta en Azure Portal
- [ ] Activar suscripción (puede ser gratuita con créditos)
- [ ] Crear Resource Group
- [ ] Crear Virtual Machine
- [ ] Configurar Network Security Group (firewall)
- [ ] Conectar por SSH
- [ ] Instalar Docker y Docker Compose
- [ ] Instalar Nginx y Certbot
- [ ] Clonar repositorio
- [ ] Configurar .env
- [ ] Configurar Nginx
- [ ] Obtener SSL (Let's Encrypt)
- [ ] Desplegar aplicación
- [ ] (Opcional) Configurar Azure Static Web Apps para frontend
- [ ] Probar endpoints
- [ ] Configurar backups (Azure Backup)

---

## 🚀 Comandos Útiles de Azure CLI

```bash
# Ver VMs
az vm list --resource-group nba-live-rg

# Iniciar VM
az vm start --resource-group nba-live-rg --name nba-live-api

# Detener VM (ahorra dinero)
az vm deallocate --resource-group nba-live-rg --name nba-live-api

# Ver IP pública
az vm show -d -g nba-live-rg -n nba-live-api --query publicIps -o tsv

# Conectar por SSH
az vm run-command invoke \
  --resource-group nba-live-rg \
  --name nba-live-api \
  --command-id RunShellScript \
  --scripts "echo 'Hello from Azure VM'"

# Ver estado de la VM
az vm show --resource-group nba-live-rg --name nba-live-api --show-details

# Crear snapshot del disco (backup)
az snapshot create \
  --resource-group nba-live-rg \
  --source nba-live-api_OsDisk \
  --name nba-live-snapshot-$(date +%Y%m%d)
```

---

## 🔐 Seguridad en Azure

1. **Network Security Groups**: Configurar en Azure Portal
2. **SSH Keys**: Azure maneja esto automáticamente
3. **IP Pública Estática**: Reservar una IP estática si necesitas
4. **Azure Backup**: Configurar backups automáticos
5. **Azure Monitor**: Monitoreo y alertas integradas

### Configurar IP Estática:

```bash
# Reservar IP pública estática
az network public-ip create \
  --resource-group nba-live-rg \
  --name nba-live-ip \
  --allocation-method Static

# Asignar a la VM
az network nic ip-config update \
  --resource-group nba-live-rg \
  --nic-name nba-live-api-nic \
  --name ipconfig1 \
  --public-ip-address nba-live-ip
```

---

## 📊 Otras Opciones de Azure (Alternativas)

### 1. Azure Container Instances (ACI)
- **Para**: Contenedores individuales
- **No soporta**: Docker Compose directamente
- **Costo**: Pago por uso (~$0.000012/GB-segundo)

### 2. Azure Container Apps
- **Para**: Aplicaciones serverless con contenedores
- **No soporta**: Docker Compose directamente
- **Costo**: Pago por uso

### 3. Azure Kubernetes Service (AKS)
- **Para**: Kubernetes (más complejo)
- **Soporta**: Docker Compose (con kompose)
- **Costo**: ~$73/mes (cluster básico) + nodos

### 4. Azure App Service (Linux)
- **Para**: Aplicaciones web
- **Soporta**: Contenedores Docker individuales
- **No soporta**: Docker Compose directamente
- **Costo**: ~$13-55/mes según plan

**Conclusión**: Para Docker Compose, **Azure Virtual Machines es la mejor opción**.

---

## 🔄 Estrategia de Migración desde Otros Proveedores

Si ya tienes la app en otro proveedor:

### Migrar a Azure:

1. **Exportar datos**:
```bash
# Backup de MySQL
docker exec nba-edge-mysql mysqldump -u user -p database > backup.sql
```

2. **Crear VM en Azure** (pasos anteriores)

3. **Transferir archivos**:
```bash
# Desde tu servidor actual
scp -r /opt/nba-live azureuser@azure-vm-ip:/opt/

# O usar Azure Storage
az storage blob upload --account-name mystorageaccount --container-name backups --name backup.sql --file backup.sql
```

4. **Restaurar datos**:
```bash
# En Azure VM
docker exec nba-edge-mysql mysql -u user -p database < backup.sql
```

---

## 📚 Recursos

- [Azure Virtual Machines Docs](https://docs.microsoft.com/azure/virtual-machines/)
- [Azure CLI Reference](https://docs.microsoft.com/cli/azure/)
- [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/)
- [Azure Free Account](https://azure.microsoft.com/free/)
- [Azure Static Web Apps](https://docs.microsoft.com/azure/static-web-apps/)

---

## ✅ Resumen

**Respuesta corta**: Sí, Azure Virtual Machines puede ejecutar Docker Compose perfectamente.

**Recomendación**:
- Si ya usas Microsoft/Azure: **Azure VM es perfecto** ($15-20/mes)
- Si no usas Microsoft: **DigitalOcean o Hetzner son más económicos** ($12 vs $15-20/mes)

El proceso es **exactamente igual** que en cualquier VPS, solo cambia el proveedor.

**Ventajas de Azure**:
- ✅ $200 de crédito gratis (30 días)
- ✅ Integración con ecosistema Microsoft
- ✅ Excelente documentación
- ✅ Muchas certificaciones de compliance
- ✅ Azure Backup integrado

**Desventajas**:
- ⚠️ Ligeramente más caro que DigitalOcean/Hetzner
- ⚠️ Curva de aprendizaje si no conoces Azure
