"""Génère eval/dataset_large.jsonl : 100 paires question/SQL sur un schéma large (> 50 colonnes).

Toutes les données sont synthétiques. Ce script ne contacte aucun service externe.
Lancer : python eval/gen_pairs.py
"""
import json
import random
from pathlib import Path

OUT = Path(__file__).parent / "dataset_large.jsonl"

# 100 paires déterministes sur le schéma large synthétique ci-dessous.
# Schéma : ventes_detail (50+ colonnes), commandes, clients, produits, employes
PAIRS: list[dict] = [
    # ── ventes_detail ──
    {"question": "Quel est le chiffre d'affaires total ?",
     "gold_sql": "SELECT ROUND(SUM(montant_ht), 2) FROM ventes_detail"},
    {"question": "Combien de lignes de vente y a-t-il ?",
     "gold_sql": "SELECT COUNT(*) FROM ventes_detail"},
    {"question": "Quel est le montant HT moyen par ligne ?",
     "gold_sql": "SELECT ROUND(AVG(montant_ht), 2) FROM ventes_detail"},
    {"question": "Quel est le montant HT maximum enregistré ?",
     "gold_sql": "SELECT MAX(montant_ht) FROM ventes_detail"},
    {"question": "Quel est le montant HT minimum enregistré ?",
     "gold_sql": "SELECT MIN(montant_ht) FROM ventes_detail"},
    {"question": "Combien de ventes ont un montant HT supérieur à 500 ?",
     "gold_sql": "SELECT COUNT(*) FROM ventes_detail WHERE montant_ht > 500"},
    {"question": "Quelle est la somme des remises accordées ?",
     "gold_sql": "SELECT ROUND(SUM(remise_montant), 2) FROM ventes_detail"},
    {"question": "Quel est le taux de remise moyen ?",
     "gold_sql": "SELECT ROUND(AVG(taux_remise), 4) FROM ventes_detail"},
    {"question": "Combien de ventes n'ont aucune remise ?",
     "gold_sql": "SELECT COUNT(*) FROM ventes_detail WHERE taux_remise = 0"},
    {"question": "Quel est le chiffre d'affaires TTC total ?",
     "gold_sql": "SELECT ROUND(SUM(montant_ttc), 2) FROM ventes_detail"},
    # ── par région ──
    {"question": "Quel est le chiffre d'affaires par région ?",
     "gold_sql": "SELECT region, ROUND(SUM(montant_ht), 2) AS ca FROM ventes_detail GROUP BY region ORDER BY ca DESC"},
    {"question": "Quelle région génère le plus de chiffre d'affaires ?",
     "gold_sql": "SELECT region FROM ventes_detail GROUP BY region ORDER BY SUM(montant_ht) DESC LIMIT 1"},
    {"question": "Combien de ventes par région ?",
     "gold_sql": "SELECT region, COUNT(*) AS n FROM ventes_detail GROUP BY region ORDER BY n DESC"},
    {"question": "Quel est le montant moyen par vente en Ontario ?",
     "gold_sql": "SELECT ROUND(AVG(montant_ht), 2) FROM ventes_detail WHERE region = 'Ontario'"},
    {"question": "Quelles régions ont un CA supérieur à 100 000 ?",
     "gold_sql": "SELECT region FROM ventes_detail GROUP BY region HAVING SUM(montant_ht) > 100000"},
    # ── par canal ──
    {"question": "Quel est le CA par canal de vente ?",
     "gold_sql": "SELECT canal, ROUND(SUM(montant_ht), 2) AS ca FROM ventes_detail GROUP BY canal ORDER BY ca DESC"},
    {"question": "Combien de ventes ont été faites en ligne ?",
     "gold_sql": "SELECT COUNT(*) FROM ventes_detail WHERE canal = 'en_ligne'"},
    {"question": "Quel canal a le panier moyen le plus élevé ?",
     "gold_sql": "SELECT canal FROM ventes_detail GROUP BY canal ORDER BY AVG(montant_ht) DESC LIMIT 1"},
    # ── par catégorie de produit ──
    {"question": "Quel est le CA par catégorie de produit ?",
     "gold_sql": "SELECT categorie_produit, ROUND(SUM(montant_ht), 2) AS ca FROM ventes_detail GROUP BY categorie_produit ORDER BY ca DESC"},
    {"question": "Quelle catégorie génère le plus de revenus ?",
     "gold_sql": "SELECT categorie_produit FROM ventes_detail GROUP BY categorie_produit ORDER BY SUM(montant_ht) DESC LIMIT 1"},
    {"question": "Combien de produits distincts ont été vendus par catégorie ?",
     "gold_sql": "SELECT categorie_produit, COUNT(DISTINCT code_produit) AS n FROM ventes_detail GROUP BY categorie_produit ORDER BY n DESC"},
    {"question": "Quelle est la quantité totale vendue par catégorie ?",
     "gold_sql": "SELECT categorie_produit, SUM(quantite) AS total_qte FROM ventes_detail GROUP BY categorie_produit ORDER BY total_qte DESC"},
    # ── par date ──
    {"question": "Quel est le CA du mois de janvier 2026 ?",
     "gold_sql": "SELECT ROUND(SUM(montant_ht), 2) FROM ventes_detail WHERE date_vente >= '2026-01-01' AND date_vente < '2026-02-01'"},
    {"question": "Quel est le CA du premier trimestre 2026 ?",
     "gold_sql": "SELECT ROUND(SUM(montant_ht), 2) FROM ventes_detail WHERE date_vente >= '2026-01-01' AND date_vente < '2026-04-01'"},
    {"question": "Quel est le CA par mois en 2026 ?",
     "gold_sql": "SELECT STRFTIME(date_vente, '%Y-%m') AS mois, ROUND(SUM(montant_ht), 2) AS ca FROM ventes_detail WHERE date_vente >= '2026-01-01' GROUP BY mois ORDER BY mois"},
    {"question": "Quel est le CA par année ?",
     "gold_sql": "SELECT YEAR(date_vente) AS annee, ROUND(SUM(montant_ht), 2) AS ca FROM ventes_detail GROUP BY annee ORDER BY annee"},
    {"question": "Combien de ventes ont été réalisées en 2026 ?",
     "gold_sql": "SELECT COUNT(*) FROM ventes_detail WHERE YEAR(date_vente) = 2026"},
    {"question": "Quel jour de la semaine génère le plus de CA ?",
     "gold_sql": "SELECT DAYOFWEEK(date_vente) AS jour, ROUND(SUM(montant_ht), 2) AS ca FROM ventes_detail GROUP BY jour ORDER BY ca DESC LIMIT 1"},
    # ── vendeurs ──
    {"question": "Quel est le CA par vendeur ?",
     "gold_sql": "SELECT id_vendeur, ROUND(SUM(montant_ht), 2) AS ca FROM ventes_detail GROUP BY id_vendeur ORDER BY ca DESC"},
    {"question": "Quel vendeur a réalisé le plus de ventes ?",
     "gold_sql": "SELECT id_vendeur FROM ventes_detail GROUP BY id_vendeur ORDER BY COUNT(*) DESC LIMIT 1"},
    {"question": "Quel est le panier moyen par vendeur ?",
     "gold_sql": "SELECT id_vendeur, ROUND(AVG(montant_ht), 2) AS panier_moyen FROM ventes_detail GROUP BY id_vendeur ORDER BY panier_moyen DESC"},
    {"question": "Combien de vendeurs distincts ont effectué des ventes ?",
     "gold_sql": "SELECT COUNT(DISTINCT id_vendeur) FROM ventes_detail"},
    # ── clients ──
    {"question": "Combien de clients distincts ont passé commande ?",
     "gold_sql": "SELECT COUNT(DISTINCT id_client) FROM ventes_detail"},
    {"question": "Quel client a généré le plus de CA ?",
     "gold_sql": "SELECT id_client FROM ventes_detail GROUP BY id_client ORDER BY SUM(montant_ht) DESC LIMIT 1"},
    {"question": "Quel est le CA moyen par client ?",
     "gold_sql": "SELECT ROUND(SUM(montant_ht) / COUNT(DISTINCT id_client), 2) FROM ventes_detail"},
    {"question": "Combien de clients ont acheté plus d'une fois ?",
     "gold_sql": "SELECT COUNT(*) FROM (SELECT id_client FROM ventes_detail GROUP BY id_client HAVING COUNT(DISTINCT id_commande) > 1)"},
    # ── commandes ──
    {"question": "Combien de commandes distinctes y a-t-il ?",
     "gold_sql": "SELECT COUNT(DISTINCT id_commande) FROM ventes_detail"},
    {"question": "Quel est le panier moyen par commande ?",
     "gold_sql": "SELECT ROUND(SUM(montant_ht) / COUNT(DISTINCT id_commande), 2) FROM ventes_detail"},
    {"question": "Quelle commande a le montant le plus élevé ?",
     "gold_sql": "SELECT id_commande FROM ventes_detail GROUP BY id_commande ORDER BY SUM(montant_ht) DESC LIMIT 1"},
    {"question": "Combien de lignes en moyenne par commande ?",
     "gold_sql": "SELECT ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT id_commande), 2) FROM ventes_detail"},
    # ── produits ──
    {"question": "Quel produit génère le plus de CA ?",
     "gold_sql": "SELECT code_produit FROM ventes_detail GROUP BY code_produit ORDER BY SUM(montant_ht) DESC LIMIT 1"},
    {"question": "Quels sont les 5 produits les plus vendus en quantité ?",
     "gold_sql": "SELECT code_produit, SUM(quantite) AS total_qte FROM ventes_detail GROUP BY code_produit ORDER BY total_qte DESC LIMIT 5"},
    {"question": "Combien de produits distincts ont été vendus ?",
     "gold_sql": "SELECT COUNT(DISTINCT code_produit) FROM ventes_detail"},
    {"question": "Quel est le prix unitaire moyen toutes ventes confondues ?",
     "gold_sql": "SELECT ROUND(AVG(prix_unitaire_ht), 2) FROM ventes_detail"},
    {"question": "Quelle est la quantité totale vendue ?",
     "gold_sql": "SELECT SUM(quantite) FROM ventes_detail"},
    # ── mode de paiement ──
    {"question": "Quelle est la répartition du CA par mode de paiement ?",
     "gold_sql": "SELECT mode_paiement, ROUND(SUM(montant_ht), 2) AS ca FROM ventes_detail GROUP BY mode_paiement ORDER BY ca DESC"},
    {"question": "Combien de ventes ont été payées par carte ?",
     "gold_sql": "SELECT COUNT(*) FROM ventes_detail WHERE mode_paiement = 'carte'"},
    # ── statut ──
    {"question": "Combien de ventes sont en statut 'retourné' ?",
     "gold_sql": "SELECT COUNT(*) FROM ventes_detail WHERE statut = 'retourne'"},
    {"question": "Quel est le CA des ventes confirmées uniquement ?",
     "gold_sql": "SELECT ROUND(SUM(montant_ht), 2) FROM ventes_detail WHERE statut = 'confirme'"},
    {"question": "Quelle proportion des ventes est annulée ?",
     "gold_sql": "SELECT ROUND(COUNT(*) FILTER (WHERE statut = 'annule') * 1.0 / COUNT(*), 4) FROM ventes_detail"},
    # ── table clients ──
    {"question": "Combien de clients sont dans la base ?",
     "gold_sql": "SELECT COUNT(*) FROM clients"},
    {"question": "Combien de clients sont en Ontario ?",
     "gold_sql": "SELECT COUNT(*) FROM clients WHERE province = 'Ontario'"},
    {"question": "Quelle province compte le plus de clients ?",
     "gold_sql": "SELECT province FROM clients GROUP BY province ORDER BY COUNT(*) DESC LIMIT 1"},
    {"question": "Combien de clients sont des entreprises (type = 'entreprise') ?",
     "gold_sql": "SELECT COUNT(*) FROM clients WHERE type_client = 'entreprise'"},
    {"question": "Quel est l'âge moyen des clients particuliers ?",
     "gold_sql": "SELECT ROUND(AVG(age), 1) FROM clients WHERE type_client = 'particulier'"},
    {"question": "Combien de clients ont été créés cette année ?",
     "gold_sql": "SELECT COUNT(*) FROM clients WHERE YEAR(date_creation) = 2026"},
    {"question": "Quelle est la répartition des clients par genre ?",
     "gold_sql": "SELECT genre, COUNT(*) AS n FROM clients GROUP BY genre ORDER BY n DESC"},
    # ── table produits ──
    {"question": "Combien de produits actifs sont dans le catalogue ?",
     "gold_sql": "SELECT COUNT(*) FROM produits WHERE actif = TRUE"},
    {"question": "Quel est le prix catalogue moyen ?",
     "gold_sql": "SELECT ROUND(AVG(prix_catalogue), 2) FROM produits"},
    {"question": "Quel est le produit le plus cher du catalogue ?",
     "gold_sql": "SELECT nom_produit FROM produits ORDER BY prix_catalogue DESC LIMIT 1"},
    {"question": "Combien de produits par fournisseur ?",
     "gold_sql": "SELECT id_fournisseur, COUNT(*) AS n FROM produits GROUP BY id_fournisseur ORDER BY n DESC"},
    {"question": "Quelle catégorie a le plus de références produit ?",
     "gold_sql": "SELECT categorie FROM produits GROUP BY categorie ORDER BY COUNT(*) DESC LIMIT 1"},
    {"question": "Quel est le poids moyen des produits ?",
     "gold_sql": "SELECT ROUND(AVG(poids_kg), 3) FROM produits"},
    # ── table commandes ──
    {"question": "Combien de commandes ont été livrées ?",
     "gold_sql": "SELECT COUNT(*) FROM commandes WHERE statut_livraison = 'livre'"},
    {"question": "Quel est le délai de livraison moyen en jours ?",
     "gold_sql": "SELECT ROUND(AVG(delai_livraison_jours), 1) FROM commandes WHERE delai_livraison_jours IS NOT NULL"},
    {"question": "Combien de commandes sont en retard ?",
     "gold_sql": "SELECT COUNT(*) FROM commandes WHERE date_livraison_reelle > date_livraison_prevue"},
    {"question": "Quel transporteur est le plus utilisé ?",
     "gold_sql": "SELECT transporteur FROM commandes GROUP BY transporteur ORDER BY COUNT(*) DESC LIMIT 1"},
    {"question": "Quel est le coût de livraison total ?",
     "gold_sql": "SELECT ROUND(SUM(cout_livraison), 2) FROM commandes"},
    # ── table employes ──
    {"question": "Combien d'employés sont dans la base ?",
     "gold_sql": "SELECT COUNT(*) FROM employes"},
    {"question": "Quel est le salaire moyen des employés ?",
     "gold_sql": "SELECT ROUND(AVG(salaire_annuel), 2) FROM employes"},
    {"question": "Combien d'employés par département ?",
     "gold_sql": "SELECT departement, COUNT(*) AS n FROM employes GROUP BY departement ORDER BY n DESC"},
    {"question": "Quel département a le salaire moyen le plus élevé ?",
     "gold_sql": "SELECT departement FROM employes GROUP BY departement ORDER BY AVG(salaire_annuel) DESC LIMIT 1"},
    {"question": "Combien d'employés sont en CDI ?",
     "gold_sql": "SELECT COUNT(*) FROM employes WHERE type_contrat = 'CDI'"},
    {"question": "Qui est l'employé le plus ancien ?",
     "gold_sql": "SELECT nom FROM employes ORDER BY date_embauche ASC LIMIT 1"},
    # ── jointures ventes_detail × clients ──
    {"question": "Quel est le CA généré par les clients entreprises ?",
     "gold_sql": "SELECT ROUND(SUM(v.montant_ht), 2) FROM ventes_detail v JOIN clients c ON v.id_client = c.id_client WHERE c.type_client = 'entreprise'"},
    {"question": "Quel est le CA généré par les clients de l'Ontario ?",
     "gold_sql": "SELECT ROUND(SUM(v.montant_ht), 2) FROM ventes_detail v JOIN clients c ON v.id_client = c.id_client WHERE c.province = 'Ontario'"},
    {"question": "Quel est le nombre de ventes par type de client ?",
     "gold_sql": "SELECT c.type_client, COUNT(*) AS n FROM ventes_detail v JOIN clients c ON v.id_client = c.id_client GROUP BY c.type_client ORDER BY n DESC"},
    # ── jointures ventes_detail × produits ──
    {"question": "Quelle est la marge brute totale ?",
     "gold_sql": "SELECT ROUND(SUM(v.montant_ht - v.quantite * p.cout_unitaire), 2) FROM ventes_detail v JOIN produits p ON v.code_produit = p.code_produit"},
    {"question": "Quel est le taux de marge moyen par catégorie ?",
     "gold_sql": "SELECT p.categorie, ROUND(AVG((v.montant_ht - v.quantite * p.cout_unitaire) / NULLIF(v.montant_ht, 0)), 4) AS taux_marge FROM ventes_detail v JOIN produits p ON v.code_produit = p.code_produit GROUP BY p.categorie ORDER BY taux_marge DESC"},
    # ── jointures ventes_detail × employes ──
    {"question": "Quel est le CA par département commercial ?",
     "gold_sql": "SELECT e.departement, ROUND(SUM(v.montant_ht), 2) AS ca FROM ventes_detail v JOIN employes e ON v.id_vendeur = e.id_employe GROUP BY e.departement ORDER BY ca DESC"},
    # ── CTEs ──
    {"question": "Quels clients ont un CA cumulé supérieur à 10 000 $ ?",
     "gold_sql": "WITH ca_client AS (SELECT id_client, SUM(montant_ht) AS ca FROM ventes_detail GROUP BY id_client) SELECT id_client FROM ca_client WHERE ca > 10000 ORDER BY ca DESC"},
    {"question": "Quel est le CA des 10 meilleurs clients ?",
     "gold_sql": "WITH top10 AS (SELECT id_client, SUM(montant_ht) AS ca FROM ventes_detail GROUP BY id_client ORDER BY ca DESC LIMIT 10) SELECT ROUND(SUM(ca), 2) FROM top10"},
    {"question": "Quel est le rang de chaque région par CA ?",
     "gold_sql": "WITH ca_region AS (SELECT region, SUM(montant_ht) AS ca FROM ventes_detail GROUP BY region) SELECT region, ca, RANK() OVER (ORDER BY ca DESC) AS rang FROM ca_region ORDER BY rang"},
    # ── agrégats avancés ──
    {"question": "Quel est l'écart-type des montants HT ?",
     "gold_sql": "SELECT ROUND(STDDEV(montant_ht), 2) FROM ventes_detail"},
    {"question": "Quels sont les déciles de montant HT ?",
     "gold_sql": "SELECT ROUND(QUANTILE_CONT(montant_ht, 0.1), 2) AS d1, ROUND(QUANTILE_CONT(montant_ht, 0.5), 2) AS median, ROUND(QUANTILE_CONT(montant_ht, 0.9), 2) AS d9 FROM ventes_detail"},
    {"question": "Combien de ventes sont au-dessus de la moyenne ?",
     "gold_sql": "SELECT COUNT(*) FROM ventes_detail WHERE montant_ht > (SELECT AVG(montant_ht) FROM ventes_detail)"},
    {"question": "Quel est le ratio CA en ligne / CA total ?",
     "gold_sql": "SELECT ROUND(SUM(CASE WHEN canal = 'en_ligne' THEN montant_ht ELSE 0 END) / NULLIF(SUM(montant_ht), 0), 4) FROM ventes_detail"},
    # ── filtrages complexes ──
    {"question": "Quels produits n'ont pas été vendus en 2026 ?",
     "gold_sql": "SELECT code_produit FROM produits WHERE code_produit NOT IN (SELECT DISTINCT code_produit FROM ventes_detail WHERE YEAR(date_vente) = 2026)"},
    {"question": "Quels clients ont acheté dans plus de 2 régions différentes ?",
     "gold_sql": "SELECT id_client FROM ventes_detail GROUP BY id_client HAVING COUNT(DISTINCT region) > 2"},
    {"question": "Quels vendeurs ont vendu dans toutes les régions ?",
     "gold_sql": "SELECT id_vendeur FROM ventes_detail GROUP BY id_vendeur HAVING COUNT(DISTINCT region) = (SELECT COUNT(DISTINCT region) FROM ventes_detail)"},
    {"question": "Quel est le CA des ventes avec remise supérieure à 10 % ?",
     "gold_sql": "SELECT ROUND(SUM(montant_ht), 2) FROM ventes_detail WHERE taux_remise > 0.10"},
    {"question": "Combien de clients n'ont jamais reçu de remise ?",
     "gold_sql": "SELECT COUNT(DISTINCT id_client) FROM ventes_detail WHERE id_client NOT IN (SELECT DISTINCT id_client FROM ventes_detail WHERE taux_remise > 0)"},
    # ── schéma large — colonnes supplémentaires ──
    {"question": "Quel est le poids total des commandes livrées ?",
     "gold_sql": "SELECT ROUND(SUM(p.poids_kg * v.quantite), 2) FROM ventes_detail v JOIN produits p ON v.code_produit = p.code_produit JOIN commandes c ON v.id_commande = c.id_commande WHERE c.statut_livraison = 'livre'"},
    {"question": "Quel est le CA généré par les clients de moins de 30 ans ?",
     "gold_sql": "SELECT ROUND(SUM(v.montant_ht), 2) FROM ventes_detail v JOIN clients c ON v.id_client = c.id_client WHERE c.age < 30"},
    {"question": "Quelle est la valeur du stock (quantite_stock × prix_catalogue) ?",
     "gold_sql": "SELECT ROUND(SUM(quantite_stock * prix_catalogue), 2) FROM produits"},
    {"question": "Combien de produits sont en rupture de stock ?",
     "gold_sql": "SELECT COUNT(*) FROM produits WHERE quantite_stock = 0"},
    {"question": "Quel est le CA par langue du client ?",
     "gold_sql": "SELECT c.langue, ROUND(SUM(v.montant_ht), 2) AS ca FROM ventes_detail v JOIN clients c ON v.id_client = c.id_client GROUP BY c.langue ORDER BY ca DESC"},
    {"question": "Quelle est la durée moyenne d'ancienneté des employés en années ?",
     "gold_sql": "SELECT ROUND(AVG(DATEDIFF('year', date_embauche, CURRENT_DATE)), 1) FROM employes"},
    {"question": "Quel est le CA par code postal du client ?",
     "gold_sql": "SELECT c.code_postal, ROUND(SUM(v.montant_ht), 2) AS ca FROM ventes_detail v JOIN clients c ON v.id_client = c.id_client GROUP BY c.code_postal ORDER BY ca DESC LIMIT 10"},
    {"question": "Combien de commandes ont été livrées en avance ?",
     "gold_sql": "SELECT COUNT(*) FROM commandes WHERE date_livraison_reelle < date_livraison_prevue"},
]

assert len(PAIRS) == 100, f"Attendu 100 paires, trouvé {len(PAIRS)}"


def main() -> None:
    rng = random.Random(42)
    shuffled = PAIRS.copy()
    rng.shuffle(shuffled)
    OUT.write_text(
        "\n".join(json.dumps(p, ensure_ascii=False) for p in shuffled) + "\n",
        encoding="utf-8",
    )
    print(f"Généré {len(PAIRS)} paires → {OUT}")


if __name__ == "__main__":
    main()
