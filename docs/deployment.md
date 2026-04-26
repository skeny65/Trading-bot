# guía de despliegue

## requisitos
* linux (ubuntu 20.04+ recomendado)
* python 3.9+
* ngrok (instalado y configurado)

## instalación
```bash
# 1. preparar servidor
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git

# 2. configurar proyecto
git clone https://github.com/tu-usuario/trading-bot.git
cd trading-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## instalar como servicio systemd
```bash
# dar permisos
chmod +x install-service.sh stop.sh

# instalar
sudo ./install-service.sh $USER

# iniciar
sudo systemctl start trading-bot@$USER
```

## configurar ngrok persistente
```bash
# autenticar
ngrok config add-authtoken tu_token

# iniciar con dominio fijo (plan pago)
ngrok http --domain=tu-dominio.ngrok.app 8000
```

## monitoreo
* logs: `sudo journalctl -u trading-bot@$USER -f`
* health: `curl http://localhost:8000/health/detailed`
* dashboard: `http://localhost:8000/dashboard`

## actualización
```bash
git pull origin main && sudo systemctl restart trading-bot@$USER
```