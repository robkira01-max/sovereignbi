# Déploiement SovereignBI

## Prérequis

- Docker 24+ et Docker Compose v2
- 24 Go RAM (pour Ollama + modèle qwen2.5-coder:32b) — 8 Go minimum avec un modèle 7B
- Pas d'accès Internet requis après la première installation

## Premier démarrage (connexion Internet requise une seule fois)

```bash
cp .env.example .env
# Éditer .env : définir des clés aléatoires
# openssl rand -hex 32 → copier la valeur dans SOVEREIGN_VIEWER_KEY, etc.

docker compose up -d ollama
docker compose exec ollama ollama pull qwen2.5-coder:32b
docker compose up -d
```

## Démarrage suivant (hors ligne)

```bash
docker compose up -d
```

Vérifier que tout est sain :

```bash
docker compose ps
curl http://localhost:8000/health
```

## Mise à jour de l'application

```bash
git pull
docker compose build api
docker compose up -d api
```

## Arrêt

```bash
docker compose down          # conserve les volumes (modèles Ollama)
docker compose down -v       # supprime aussi les volumes
```

## Variables d'environnement obligatoires

| Variable | Rôle |
|---|---|
| `SOVEREIGN_VIEWER_KEY` | Clé API lecture seule (`/ask`, `/upload`) |
| `SOVEREIGN_EDITOR_KEY` | Clé API lecture + écriture (dashboards, feedback) |
| `SOVEREIGN_ADMIN_KEY` | Clé API administration (modèle sémantique, propositions) |
| `LLM_MODEL` | Nom du modèle Ollama (ex. `qwen2.5-coder:32b`) |
| `OLLAMA_URL` | URL interne Ollama (laisser `http://ollama:11434` par défaut) |

## Isolation réseau

Le conteneur `ollama` est sur le réseau `internal` (pas d'accès Internet).
Le conteneur `api` est sur `internal` + `exposed` (pour publier le port 8000) mais n'émet aucun appel sortant.

### Vérification de la non-sortie réseau (hôte Linux/ufw)

```bash
# Bloquer les connexions sortantes depuis le conteneur api (sauf vers ollama)
sudo ufw deny out from <ip_container_api> to any
sudo ufw allow out from <ip_container_api> to <ip_container_ollama>

# Vérifier en temps réel
sudo ss -tnp | grep $(docker inspect --format '{{.State.Pid}}' sovereignbi-api-1)
```

### Vérification sans pare-feu

```bash
# 24 h de monitoring : aucune connexion sortante ne doit apparaître
docker run --rm --network container:sovereignbi-api-1 nicolaka/netshoot \
  tcpdump -n 'not dst net 172.16.0.0/12 and not dst net 10.0.0.0/8'
```

## Chiffrement disque (recommandé en production)

Les données sont stockées dans les volumes Docker. Pour une protection maximale :

```bash
# Ubuntu/Debian : activer LUKS sur le volume Docker
sudo systemctl stop docker
sudo cryptsetup luksFormat /dev/sdX
sudo cryptsetup open /dev/sdX docker_data
sudo mkfs.ext4 /dev/mapper/docker_data
# Monter sur /var/lib/docker
```

## Plan de reprise (PRA)

- Sauvegarder les volumes Docker régulièrement : `docker run --rm -v ollama_models:/data -v $(pwd):/backup alpine tar czf /backup/ollama_backup.tar.gz /data`
- Les fichiers YAML des dashboards (`data/dashboards/`) et le modèle sémantique (`semantic/model.yaml`) doivent être inclus dans les sauvegardes.
- RTO cible : < 1 h (réinstallation depuis zéro avec sauvegarde).
- RPO cible : < 24 h (sauvegarde quotidienne).
