#!/usr/bin/env bash
# SovereignBI — Bootstrap Oracle Cloud Free Tier ARM (Ubuntu 22.04 aarch64)
#
# Usage (depuis votre machine locale) :
#   ssh ubuntu@VOTRE_IP_ORACLE "bash -s" < tools/setup-oracle-server.sh
#
# Ou directement sur le serveur :
#   curl -fsSL https://raw.githubusercontent.com/robkira01-max/sovereignbi/master/tools/setup-oracle-server.sh | bash
#
# Ce script :
#   1. Installe Docker Engine + Compose V2
#   2. Configure le pare-feu (ports 80, 443, 22)
#   3. Clone le dépôt SovereignBI
#   4. Crée le fichier .env depuis .env.prod.example
#   5. Build et démarre les conteneurs
#   6. Charge les données INSTAD pilote
#   7. Affiche l'URL et les clés d'accès

set -euo pipefail

REPO_URL="https://github.com/robkira01-max/sovereignbi.git"
INSTALL_DIR="/opt/sovereignbi"
DOMAIN="${DOMAIN:-}"
GROQ_API_KEY="${GROQ_API_KEY:-}"

echo "╔══════════════════════════════════════════════════╗"
echo "║   SovereignBI — Installation Oracle Cloud ARM    ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── 1. Mise à jour système ────────────────────────────────────────────────────
echo "[1/7] Mise à jour du système..."
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# ── 2. Docker Engine ──────────────────────────────────────────────────────────
echo "[2/7] Installation de Docker..."
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    echo "  ✓ Docker installé"
else
    echo "  ✓ Docker déjà présent ($(docker --version))"
fi

# Docker Compose V2 (plugin)
if ! docker compose version &>/dev/null 2>&1; then
    sudo apt-get install -y -qq docker-compose-plugin
fi
echo "  ✓ Docker Compose $(docker compose version --short)"

# ── 3. Pare-feu Oracle (iptables + règles UFW) ────────────────────────────────
echo "[3/7] Configuration du pare-feu..."
sudo iptables -I INPUT -p tcp --dport 80  -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT -p udp --dport 443 -j ACCEPT 2>/dev/null || true
# Rendre persistant
if command -v netfilter-persistent &>/dev/null; then
    sudo netfilter-persistent save
elif dpkg -l iptables-persistent &>/dev/null 2>&1; then
    sudo iptables-save | sudo tee /etc/iptables/rules.v4 > /dev/null
else
    sudo apt-get install -y -qq iptables-persistent
    sudo iptables-save | sudo tee /etc/iptables/rules.v4 > /dev/null
fi
echo "  ✓ Ports 80/443 ouverts"

# ── 4. Clonage du dépôt ───────────────────────────────────────────────────────
echo "[4/7] Clonage du dépôt..."
sudo mkdir -p "$INSTALL_DIR"
sudo chown "$USER:$USER" "$INSTALL_DIR"
if [ -d "$INSTALL_DIR/.git" ]; then
    cd "$INSTALL_DIR" && git pull --quiet
    echo "  ✓ Dépôt mis à jour"
else
    git clone --quiet "$REPO_URL" "$INSTALL_DIR"
    echo "  ✓ Dépôt cloné dans $INSTALL_DIR"
fi
cd "$INSTALL_DIR"

# ── 5. Configuration .env ─────────────────────────────────────────────────────
echo "[5/7] Configuration de l'environnement..."
if [ ! -f .env ]; then
    cp .env.prod.example .env

    # Générer des clés aléatoires
    VIEWER_KEY=$(openssl rand -hex 24)
    EDITOR_KEY=$(openssl rand -hex 24)
    ADMIN_KEY=$(openssl rand -hex 24)
    CERT_SECRET=$(openssl rand -hex 32)
    VAULT_KEY=$(openssl rand -hex 32)

    sed -i "s/CHANGEME_viewer_32chars_random/$VIEWER_KEY/" .env
    sed -i "s/CHANGEME_editor_32chars_random/$EDITOR_KEY/" .env
    sed -i "s/CHANGEME_admin_32chars_random/$ADMIN_KEY/" .env
    sed -i "s/CHANGEME_cert_secret_32chars/$CERT_SECRET/" .env
    sed -i "s/CHANGEME_vault_key_32chars_random/$VAULT_KEY/" .env

    # Domaine
    if [ -n "$DOMAIN" ]; then
        sed -i "s/sovereignbi.votre-domaine.example.com/$DOMAIN/g" .env
    else
        # Utiliser nip.io avec l'IP publique
        PUBLIC_IP=$(curl -s https://api.ipify.org || curl -s https://ipv4.icanhazip.com)
        NIP_DOMAIN="${PUBLIC_IP//./-}.nip.io"
        sed -i "s/sovereignbi.votre-domaine.example.com/$NIP_DOMAIN/g" .env
        DOMAIN="$NIP_DOMAIN"
    fi
    sed -i "s/admin@votre-domaine.example.com/admin@${DOMAIN}/" .env

    # Groq API key
    if [ -n "$GROQ_API_KEY" ]; then
        sed -i "s/gsk_VOTRE_CLE_GROQ/$GROQ_API_KEY/" .env
    fi

    echo "  ✓ .env créé"
    echo ""
    echo "  ⚠  Clés générées (à noter dans un endroit sûr) :"
    echo "     SOVEREIGN_VIEWER_KEY : $VIEWER_KEY"
    echo "     SOVEREIGN_EDITOR_KEY : $EDITOR_KEY"
    echo "     SOVEREIGN_ADMIN_KEY  : $ADMIN_KEY"
    echo ""
else
    echo "  ✓ .env existant conservé"
fi

# Vérifier que KIMI_API_KEY est remplie
if grep -q "gsk_VOTRE_CLE_GROQ" .env; then
    echo ""
    echo "  ❌ KIMI_API_KEY manquante dans .env"
    echo "     Récupérez votre clé Groq gratuite sur : https://console.groq.com"
    echo "     Puis : sed -i 's/gsk_VOTRE_CLE_GROQ/VOTRE_CLE/' /opt/sovereignbi/.env"
    echo ""
fi

# ── 6. Build et démarrage ─────────────────────────────────────────────────────
echo "[6/7] Build Docker et démarrage..."
docker compose -f docker-compose.prod.yml build --quiet
docker compose -f docker-compose.prod.yml up -d
echo "  ✓ Conteneurs démarrés"

# Attendre que l'API soit saine
echo "  ↳ Attente du démarrage API (max 60s)..."
for i in $(seq 1 12); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "  ✓ API répond"
        break
    fi
    sleep 5
done

# ── 7. Chargement données INSTAD ──────────────────────────────────────────────
echo "[7/7] Chargement des données INSTAD pilote..."
if [ -f "tools/load_instad_datasets.py" ]; then
    docker compose -f docker-compose.prod.yml exec -T api \
        python tools/load_instad_datasets.py --target /srv/data/instad/ 2>&1 | tail -5
    echo "  ✓ Données INSTAD chargées"
fi

# ── Résumé ────────────────────────────────────────────────────────────────────
DOMAIN_USED=$(grep "^DOMAIN=" .env | cut -d= -f2)
ADMIN_KEY_USED=$(grep "^SOVEREIGN_ADMIN_KEY=" .env | cut -d= -f2)
EDITOR_KEY_USED=$(grep "^SOVEREIGN_EDITOR_KEY=" .env | cut -d= -f2)

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║            SovereignBI — DÉPLOYÉ ✓               ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  URL         : https://$DOMAIN_USED"
echo "  Health      : https://$DOMAIN_USED/health"
echo "  Interface   : https://$DOMAIN_USED/app/"
echo "  API docs    : https://$DOMAIN_USED/docs"
echo ""
echo "  Clé Admin   : $ADMIN_KEY_USED"
echo "  Clé Éditeur : $EDITOR_KEY_USED"
echo ""
echo "  Commandes utiles :"
echo "    Logs      : docker compose -f docker-compose.prod.yml logs -f api"
echo "    Restart   : docker compose -f docker-compose.prod.yml restart api"
echo "    Mise à jour :"
echo "      git pull && docker compose -f docker-compose.prod.yml build api"
echo "      docker compose -f docker-compose.prod.yml up -d api"
echo ""
echo "  📋 INSTAD — Pour créer une instance pilote :"
echo "    Partagez la clé Éditeur à l'analyste INSTAD."
echo "    Ils uploadent leurs fichiers Excel sur /app/ → Upload."
