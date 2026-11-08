# P-027 — Connecteur Statistique Canada (WDS) — 7 novembre 2026

Raison : les données de Statistique Canada sont en accès libre sous Licence
ouverte (usage commercial permis, sans frais, avec attribution) et accessibles
sans clé via le Web Data Service. Elles donnent à MizanBI un vrai jeu de
données réel, propre et bien documenté — chômage, population, IPC — pour
tester la couche sémantique, le harnais d'évaluation et le certificat de
précision, au lieu de ne s'appuyer que sur les chiffres démo de Djibouti.
Elles servent aussi de deuxième template (Canada), sans toucher au pilote
INSTAD.

Impact : moyen — connecteur documenté + snapshot local + page Canada.
Zéro dépendance nouvelle, zéro clé, zéro appel réseau en mode démo.

Statut : livré 2026-11-07. `src/lib/statcan.ts`, `src/data/statcan/`
(4 JSON, 16 Ko), `src/pages/Canada.tsx`, `docs/statcan-p027.md`.
Tables vérifiées en direct : 14-10-0287-01 (chômage mensuel par province),
17-10-0009-01 (population trimestrielle), 18-10-0004-01 (IPC mensuel).
Changement documenté : 14-10-0327-01 remplacée (annuelle par âge, pas
mensuelle par province) par 14-10-0287-01.

Règles : attribution « Source : Statistique Canada, [nom], [date] » sur
chaque tuile ; reproduction fidèle ; aucune suggestion d'approbation ;
chiffres canadiens jamais mélangés aux chiffres démo Djibouti ;
snapshot figé au 7 nov. 2026, à rafraîchir (voir README).
