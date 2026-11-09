# Questions en attente — MizanBI

## Q-001 — Droits de redistribution des données embarquées dans mizanbi-client

**Date :** 2026-11-09  
**Impact :** Bloquant pour toute diffusion publique de mizanbi-client (npm build publié, image Docker publique, Vercel).

Les données suivantes sont embarquées dans `mizanbi-client/src/data/` et distribuées avec le bundle JS :

| Source | Fichier(s) | Licence déclarée | Redistribution commerciale ? |
|--------|-----------|-----------------|------------------------------|
| BIE — Bulletins d'information économique (Ministère des Finances DJ, 2001–2012) | `bie/bie_series.json`, `bie/bie_sources.json` | Non documentée — données gouvernementales DJ | **À confirmer** |
| BCD — Rapport Annuel 2024 + INSTAD RGPH-3 | `bcd/bcd_data.json` | Non documentée — données BCD/INSTAD DJ | **À confirmer** |
| StatCan — Statistique Canada, snapshot nov. 2026 | `statcan/statcan_*.json` | [Licence d'utilisation des données de Statistique Canada](https://www.statcan.gc.ca/fra/reference/licence) — redistribution des extraits autorisée avec attribution | ✅ Attribution présente dans l'UI |

**Actions requises du propriétaire :**
1. BIE : contacter le Ministère des Finances DJ pour obtenir une autorisation écrite de redistribution des données BIE dans un produit commercial.
2. BCD : idem pour la Banque Centrale de Djibouti.
3. StatCan : vérifier que l'attribution actuelle dans `Bulletins.tsx` satisfait les conditions (mention « ne cautionne pas »).

**En attendant :** mizanbi-client peut être utilisé en interne (INSTAD) mais pas publié publiquement avec ces données embarquées.

---

## Q-002 — Choix du frontend livré : `frontend/` vs `mizanbi-client/`

**Date :** 2026-11-09  
**Impact :** Bloquant pour le déploiement Oracle.

- `frontend/` : MapLibre GL, frontend complet, URL de prod en dur (`https://sovereignbi-api.147-5-126-188.sslip.io`), pas de compte utilisateur, Dockerfile existant.
- `mizanbi-client/` : React standalone (sans MapLibre), comptes utilisateurs (login/admin), i18n fr/en/ar, données BIE/BCD/StatCan embarquées, Dockerfile ajouté (2026-11-09).

**Question :** Lequel déployer sur Oracle ? Les deux peuvent coexister derrière Caddy (ports distincts).

---

## Q-003 — Relecture arabe par un arabophone

**Date :** 2026-11-09  
**Concerne :** Sections GeoAI (`geoai.*`), Comptes (`admin.*`), Changer mot de passe (`changePwd.*`) dans `mizanbi-client/src/lib/i18n.ts`.  
**Priorité :** Avant tout déploiement face à des utilisateurs arabophones.
