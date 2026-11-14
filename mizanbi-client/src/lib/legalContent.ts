import { LEGAL, type LegalConfig } from './legalConfig'
import type { Lang } from './i18n'

export type LegalKind = 'privacy' | 'terms' | 'cookies' | 'legal'

export interface LegalSection {
  title: string
  paragraphs?: string[]
  bullets?: string[]
  /** Paragraphe affiché après la liste. */
  after?: string
}

export interface LegalDoc {
  title: string
  sections: LegalSection[]
}

/** Remplace {{clé}} par la valeur de LEGAL (jeton inconnu = erreur visible, jamais silencieuse). */
export function fill(text: string, cfg: LegalConfig = LEGAL): string {
  return text.replace(/\{\{(\w+)\}\}/g, (_, key: string) => {
    const v = (cfg as unknown as Record<string, unknown>)[key]
    if (typeof v !== 'string') throw new Error(`Jeton juridique inconnu : {{${key}}}`)
    return v
  })
}

// ───────────────────────────── FRANÇAIS ─────────────────────────────

const PRIVACY_FR: LegalDoc = {
  title: 'Politique de confidentialité',
  sections: [
    {
      title: '1. Introduction',
      paragraphs: [
        "MizanBI est une plateforme de Business Intelligence assistée par intelligence artificielle, permettant aux organisations d'importer, de traiter, d'analyser et de visualiser leurs données.",
        "La protection des renseignements personnels et la confidentialité des données professionnelles constituent des priorités. La présente politique explique quelles informations sont collectées, pourquoi elles sont utilisées, comment elles sont protégées et quels sont les droits des utilisateurs.",
      ],
    },
    {
      title: '2. Responsable du traitement',
      bullets: [
        'Organisation : {{company}}',
        'Produit : MizanBI',
        'Adresse : {{address}}',
        'Courriel : {{privacyEmail}}',
        'Responsable de la protection des renseignements personnels : {{privacyOfficer}}',
      ],
    },
    {
      title: '3. Informations collectées',
      paragraphs: ['Selon les fonctionnalités utilisées, MizanBI peut collecter les catégories d’informations suivantes.'],
      bullets: [
        'Compte : adresse électronique professionnelle, nom affiché, rôle, mot de passe (conservé uniquement sous forme hachée) et organisation. Les informations d’abonnement ou de facturation ne sont collectées que si l’offre commerciale souscrite l’exige.',
        'Techniques : adresse IP, type de navigateur, journaux techniques, date et heure de connexion, informations relatives aux erreurs.',
        'Données importées : fichiers CSV, Excel, PDF, bases de données, données professionnelles et statistiques. L’utilisateur demeure responsable de disposer des droits nécessaires pour les importer et les traiter.',
      ],
      after: 'Le stockage local du navigateur (session, préférences) est décrit dans la politique relative aux cookies.',
    },
    {
      title: '4. Finalités du traitement',
      bullets: [
        'Créer et administrer les comptes.',
        'Fournir les fonctionnalités de Business Intelligence et générer des analyses et visualisations.',
        'Répondre aux demandes des utilisateurs.',
        'Assurer la sécurité de la plateforme, détecter les erreurs et les utilisations abusives.',
        'Gérer les abonnements et la facturation, lorsque cela est applicable.',
        'Améliorer les performances et la fiabilité du service.',
      ],
    },
    {
      title: '5. Intelligence artificielle et traitement des données',
      paragraphs: [
        'MizanBI utilise des technologies d’intelligence artificielle pour faciliter l’analyse des données et générer des réponses en langage naturel. Deux modes existent, selon l’installation :',
      ],
      bullets: [
        'Mode local : le modèle s’exécute sur l’infrastructure de l’installation. Aucune donnée n’est transmise à un tiers.',
        'Mode externe : les questions et les extraits de données nécessaires à la réponse sont transmis au fournisseur d’IA configuré. Fournisseur : {{aiProvider}}. Pays de traitement : {{aiCountry}}.',
      ],
      after: 'Les résultats produits par l’IA peuvent comporter des erreurs et doivent être vérifiés avant toute décision importante. Les données des clients ne sont pas utilisées pour entraîner des modèles d’IA sans base juridique appropriée et, lorsque nécessaire, consentement ou autorisation. L’avis de confidentialité de l’instance indique le mode actif.',
    },
    {
      title: '6. Hébergement et transferts de données',
      paragraphs: [
        'MizanBI peut être déployé sur l’infrastructure locale du client, sur un serveur privé, sur une infrastructure cloud contrôlée par le client ou sous forme d’hébergement géré par le fournisseur.',
        'Hébergement de la présente instance : {{host}} — région : {{hostRegion}}.',
        'Les sous-traitants et les éventuels transferts internationaux (notamment vers le fournisseur d’IA externe lorsque le mode externe est activé) sont communiqués dans les informations contractuelles applicables. Lorsque la loi l’exige, une évaluation des facteurs relatifs à la vie privée est réalisée avant tout transfert hors du Québec.',
      ],
    },
    {
      title: '7. Conservation des données',
      paragraphs: ['Les informations sont conservées uniquement pendant la durée nécessaire aux finalités prévues, sous réserve des obligations légales et contractuelles.'],
      bullets: [
        'Comptes : {{retentionAccounts}}',
        'Journaux techniques : {{retentionLogs}}',
        'Données importées : {{retentionData}}',
      ],
    },
    {
      title: '8. Sécurité',
      paragraphs: ['MizanBI met en œuvre, selon le déploiement et les fonctionnalités activées, des mesures de protection comprenant notamment :'],
      bullets: [
        'Contrôle des accès, authentification et gestion des permissions par rôle.',
        'Mots de passe et jetons de session conservés sous forme hachée.',
        'Chiffrement des communications et protection des interfaces API.',
        'Journalisation des événements de sécurité.',
        'Sauvegardes et mises à jour de sécurité.',
      ],
      after: 'Aucun système informatique ne peut garantir une sécurité absolue.',
    },
    {
      title: '9. Droits des utilisateurs',
      paragraphs: ['Sous réserve de la législation applicable, les utilisateurs peuvent notamment demander :'],
      bullets: [
        'L’accès à leurs renseignements personnels.',
        'La rectification des informations inexactes.',
        'La suppression des informations lorsque cela est applicable.',
        'Le retrait de leur consentement.',
        'Des renseignements sur les utilisations et communications de leurs données.',
        'La portabilité de leurs données lorsque la loi le prévoit.',
        'Le dépôt d’une plainte auprès de l’autorité compétente : {{authority}}.',
      ],
      after: 'Les demandes peuvent être adressées à : {{privacyEmail}}',
    },
    {
      title: '10. Incidents de confidentialité',
      paragraphs: [
        'En cas d’incident de confidentialité présentant un risque de préjudice sérieux, l’autorité compétente et les personnes concernées sont avisées dans les meilleurs délais, conformément à la législation applicable. Un registre des incidents est tenu.',
      ],
    },
    {
      title: '11. Mineurs',
      paragraphs: ['MizanBI est un produit professionnel destiné aux organisations et aux utilisateurs autorisés. Il n’est pas conçu pour être utilisé de manière autonome par des enfants.'],
    },
    {
      title: '12. Modifications',
      paragraphs: ['Cette politique peut être mise à jour pour refléter les évolutions légales, techniques ou commerciales de MizanBI. La date de dernière mise à jour est indiquée en haut de cette page.'],
    },
    {
      title: '13. Contact',
      paragraphs: ['Pour toute question concernant la confidentialité : {{privacyEmail}}'],
    },
  ],
}

const TERMS_FR: LegalDoc = {
  title: 'Conditions générales d’utilisation',
  sections: [
    {
      title: '1. Objet',
      paragraphs: ['Les présentes conditions définissent les règles d’accès et d’utilisation de MizanBI, plateforme de Business Intelligence permettant aux organisations de connecter leurs données, de produire des analyses, de créer des visualisations et d’utiliser des fonctionnalités d’intelligence artificielle.'],
    },
    {
      title: '2. Acceptation',
      paragraphs: [
        'L’accès à la plateforme implique l’acceptation des présentes conditions. L’acceptation est demandée à la première connexion et à chaque nouvelle version ; elle est enregistrée (compte, date et version acceptée).',
        'L’utilisateur qui n’accepte pas ces conditions doit cesser d’utiliser le service.',
      ],
    },
    {
      title: '3. Accès à la plateforme',
      paragraphs: ['L’accès à MizanBI peut être proposé sous forme d’installation locale, de déploiement sur infrastructure privée, d’hébergement cloud, ou d’offre commerciale sous licence annuelle par installation ou abonnement. Les fonctionnalités disponibles dépendent de l’offre souscrite et de la configuration technique.'],
    },
    {
      title: '4. Création et sécurité du compte',
      paragraphs: ['L’utilisateur s’engage à :'],
      bullets: ['Fournir des informations exactes.', 'Protéger ses identifiants.', 'Ne pas partager son compte sans autorisation.', 'Signaler toute utilisation non autorisée.', 'Respecter les permissions attribuées.'],
      after: 'L’organisation cliente est responsable de la gestion des utilisateurs qu’elle autorise.',
    },
    {
      title: '5. Utilisation autorisée',
      paragraphs: ['L’utilisateur s’engage à utiliser MizanBI conformément aux lois applicables. Il est notamment interdit de :'],
      bullets: [
        'Utiliser la plateforme pour des activités illégales.',
        'Tenter de contourner les mécanismes de sécurité.',
        'Accéder aux données d’autres utilisateurs sans autorisation.',
        'Introduire des logiciels malveillants.',
        'Exploiter les vulnérabilités de la plateforme.',
        'Utiliser le service pour compromettre des systèmes tiers.',
      ],
    },
    {
      title: '6. Données importées par les utilisateurs',
      paragraphs: [
        'L’utilisateur conserve les droits qu’il détient sur les données qu’il importe dans MizanBI et garantit disposer des autorisations nécessaires pour leur utilisation.',
        'MizanBI n’acquiert aucun droit de propriété sur les données importées du seul fait de leur traitement. Le fournisseur traite ces données uniquement dans le cadre des finalités autorisées par le contrat et les paramètres applicables.',
      ],
    },
    {
      title: '7. Intelligence artificielle et résultats',
      paragraphs: ['Les résultats générés par l’intelligence artificielle sont fournis à titre d’assistance analytique. Ils peuvent contenir des erreurs, des omissions ou des interprétations incorrectes. L’utilisateur doit les vérifier avant de les utiliser pour :'],
      bullets: ['Des décisions financières.', 'Des décisions administratives.', 'Des décisions médicales.', 'Des décisions juridiques.', 'Des décisions opérationnelles importantes.'],
      after: 'MizanBI ne garantit pas l’exactitude absolue des réponses générées par l’IA.',
    },
    {
      title: '8. Disponibilité du service',
      paragraphs: ['Des interruptions peuvent survenir pour des raisons de maintenance, de sécurité, de mise à jour ou de défaillance technique. Les conditions de disponibilité, de sauvegarde, de support et de rétablissement sont définies dans les contrats applicables.'],
    },
    {
      title: '9. Propriété intellectuelle',
      paragraphs: [
        'Les éléments propres à MizanBI (code, interface, identité visuelle, logos, documentation) sont protégés par les droits de propriété intellectuelle applicables. Toute reproduction ou exploitation non autorisée est interdite.',
        'Les données appartenant aux utilisateurs restent soumises aux droits de leurs propriétaires respectifs. Les composants open source restent soumis à leurs licences respectives.',
      ],
    },
    {
      title: '10. Services tiers et données publiques',
      paragraphs: [
        'Certaines installations utilisent des services ou logiciels tiers, soumis à leurs propres conditions et licences. Leur utilisation ne signifie pas que leurs fournisseurs sont affiliés à MizanBI.',
        'MizanBI intègre des jeux de données publics ou institutionnels (notamment INSTAD, Banque Centrale de Djibouti, Statistique Canada, CERD, OpenStreetMap) fournis à titre informatif, avec mention de leur source et sous leurs licences d’origine. Ces sources ne cautionnent pas MizanBI, et leur exactitude n’est pas garantie.',
      ],
    },
    {
      title: '11. Suspension et résiliation',
      paragraphs: ['L’accès peut être suspendu ou résilié en cas de violation grave des présentes conditions, d’utilisation frauduleuse, d’atteinte à la sécurité, de défaut de paiement lorsque cela est applicable, ou d’obligation légale ou réglementaire. Les modalités de récupération et de suppression des données sont définies dans le contrat applicable.'],
    },
    {
      title: '12. Limitation de responsabilité',
      paragraphs: ['Dans les limites autorisées par la législation applicable, le fournisseur ne garantit pas que les résultats analytiques ou générés par l’IA seront exempts d’erreurs. Aucune disposition des présentes conditions ne vise à exclure une responsabilité qui ne peut légalement être exclue ou limitée.'],
    },
    {
      title: '13. Modifications des conditions',
      paragraphs: ['Les présentes conditions peuvent être modifiées pour tenir compte de l’évolution du produit, de ses fonctionnalités ou des obligations légales. La nouvelle version est publiée sur le site et son acceptation est redemandée.'],
    },
    {
      title: '14. Droit applicable',
      paragraphs: ['Les présentes conditions sont soumises au droit suivant : {{law}}, sous réserve des règles impératives applicables aux utilisateurs.'],
    },
    {
      title: '15. Contact',
      paragraphs: ['Pour toute question concernant les présentes conditions : {{contactEmail}}'],
    },
  ],
}

const COOKIES_FR: LegalDoc = {
  title: 'Politique relative aux cookies et au stockage local',
  sections: [
    {
      title: '1. Qu’est-ce qu’un cookie ?',
      paragraphs: ['Un cookie est un petit fichier enregistré sur le terminal d’un utilisateur lorsqu’il visite un site Internet. Une application web peut aussi conserver des informations dans le « stockage local » du navigateur (localStorage et sessionStorage), qui joue un rôle comparable.'],
    },
    {
      title: '2. Ce que MizanBI utilise réellement',
      paragraphs: ['MizanBI ne dépose aucun cookie HTTP. Il utilise uniquement le stockage local du navigateur ci-dessous, tous strictement nécessaires au fonctionnement ou à vos préférences :'],
      bullets: [
        'mizan_token (sessionStorage) — jeton de session de votre connexion. Supprimé à la fermeture de l’onglet ou à la déconnexion.',
        'mizan_email et mizan_user_name (localStorage) — identité affichée dans l’interface. Supprimés à la déconnexion.',
        'mizan_theme_mode (localStorage) — votre préférence d’affichage (thème).',
        'mizan_cookie_consent (localStorage) — mémorise votre choix concernant les cookies.',
        'mizan_terms_accepted (localStorage) — mémorise la version des conditions d’utilisation que vous avez acceptée.',
        'mizan_ancient_maps_v1 (localStorage) — données que vous saisissez dans la fonction « Cartes anciennes ». Elles restent dans votre navigateur.',
      ],
    },
    {
      title: '3. Ce que MizanBI n’utilise pas',
      bullets: [
        'Aucun cookie analytique et aucun cookie marketing ou publicitaire.',
        'Aucun traceur tiers.',
        'Aucun service tiers chargé automatiquement par le navigateur : les polices des cartes et les fonds de carte sont hébergés avec l’application.',
      ],
    },
    {
      title: '4. Consentement',
      paragraphs: [
        'Le stockage local ci-dessus est strictement nécessaire : il ne requiert pas de consentement. Aucune catégorie facultative n’est active par défaut. L’opérateur de l’instance peut activer une mesure d’audience sans cookie (Plausible ou Umami) ; elle ne se charge alors qu’après votre acceptation, et le retrait de votre consentement l’arrête.',
        'Le refus des éléments non essentiels ne doit pas empêcher l’accès aux fonctionnalités essentielles.',
      ],
    },
    {
      title: '5. Gérer mes préférences',
      paragraphs: ['Vous pouvez modifier votre choix à tout moment avec le bouton « Gérer mes cookies » ci-dessous ou en pied de page, et supprimer les données du stockage local depuis les paramètres de votre navigateur.'],
    },
    {
      title: '6. Contact',
      paragraphs: ['Pour toute question : {{privacyEmail}}'],
    },
  ],
}

const LEGAL_FR: LegalDoc = {
  title: 'Mentions légales',
  sections: [
    {
      title: 'Éditeur',
      bullets: [
        'Éditeur : {{company}}',
        'Nom commercial : MizanBI',
        'Adresse : {{address}}',
        'Courriel : {{contactEmail}}',
        'Téléphone : {{phone}}',
        'Numéro d’enregistrement : {{registration}}',
        'Responsable de publication : {{publisher}}',
      ],
    },
    {
      title: 'Hébergement',
      paragraphs: ['{{host}} — région : {{hostRegion}}'],
    },
    {
      title: 'Propriété intellectuelle',
      paragraphs: [
        'MizanBI et les éléments originaux de son interface sont protégés par les droits applicables. Les composants tiers demeurent soumis à leurs licences respectives (voir le fichier THIRD_PARTY du produit).',
        'Les données cartographiques et statistiques affichées indiquent leur source et leur licence sous chaque carte ou tableau (CERD, OpenStreetMap — © contributeurs OpenStreetMap, ODbL —, INSTAD, Banque Centrale de Djibouti, Statistique Canada).',
      ],
    },
  ],
}

// ───────────────────────────── ENGLISH ─────────────────────────────

const PRIVACY_EN: LegalDoc = {
  title: 'Privacy Policy',
  sections: [
    {
      title: '1. Introduction',
      paragraphs: [
        'MizanBI is an AI-assisted Business Intelligence platform that lets organisations import, process, analyse and visualise their data.',
        'Protecting personal information and the confidentiality of professional data is a priority. This policy explains what information is collected, why it is used, how it is protected, and what rights users have.',
      ],
    },
    {
      title: '2. Data controller',
      bullets: [
        'Organisation: {{company}}',
        'Product: MizanBI',
        'Address: {{address}}',
        'Email: {{privacyEmail}}',
        'Person responsible for the protection of personal information: {{privacyOfficer}}',
      ],
    },
    {
      title: '3. Information collected',
      paragraphs: ['Depending on the features used, MizanBI may collect the following categories of information.'],
      bullets: [
        'Account: professional email address, display name, role, password (stored only in hashed form) and organisation. Subscription or billing information is collected only if the commercial offer requires it.',
        'Technical: IP address, browser type, technical logs, connection date and time, error information.',
        'Imported data: CSV files, Excel files, PDFs, databases, professional and statistical data. The user remains responsible for holding the rights needed to import and process them.',
      ],
      after: 'Browser local storage (session, preferences) is described in the cookie policy.',
    },
    {
      title: '4. Purposes of processing',
      bullets: [
        'Create and administer accounts.',
        'Provide Business Intelligence features and generate analyses and visualisations.',
        'Respond to user requests.',
        'Ensure platform security and detect errors and abuse.',
        'Manage subscriptions and billing, where applicable.',
        'Improve performance and reliability of the service.',
      ],
    },
    {
      title: '5. Artificial intelligence and data processing',
      paragraphs: ['MizanBI uses artificial intelligence to help analyse data and generate natural-language answers. Two modes exist, depending on the installation:'],
      bullets: [
        'Local mode: the model runs on the installation’s own infrastructure. No data is sent to a third party.',
        'External mode: the questions and the data excerpts needed for the answer are sent to the configured AI provider. Provider: {{aiProvider}}. Country of processing: {{aiCountry}}.',
      ],
      after: 'AI output may contain errors and must be verified before any important decision. Customer data is not used to train AI models without an appropriate legal basis and, where required, consent or authorisation. The instance’s privacy notice states the active mode.',
    },
    {
      title: '6. Hosting and data transfers',
      paragraphs: [
        'MizanBI can be deployed on the customer’s local infrastructure, on a private server, on cloud infrastructure controlled by the customer, or as hosting managed by the provider.',
        'Hosting of this instance: {{host}} — region: {{hostRegion}}.',
        'Sub-processors and any international transfers (notably to the external AI provider when external mode is enabled) are disclosed in the applicable contractual information. Where the law requires it, a privacy impact assessment is carried out before any transfer outside Québec.',
      ],
    },
    {
      title: '7. Data retention',
      paragraphs: ['Information is kept only for as long as needed for the stated purposes, subject to legal and contractual obligations.'],
      bullets: [
        'Accounts: {{retentionAccounts}}',
        'Technical logs: {{retentionLogs}}',
        'Imported data: {{retentionData}}',
      ],
    },
    {
      title: '8. Security',
      paragraphs: ['Depending on the deployment and the features enabled, MizanBI applies protection measures including:'],
      bullets: [
        'Access control, authentication and role-based permissions.',
        'Passwords and session tokens stored in hashed form.',
        'Encryption of communications and protection of API interfaces.',
        'Logging of security events.',
        'Backups and security updates.',
      ],
      after: 'No information system can guarantee absolute security.',
    },
    {
      title: '9. User rights',
      paragraphs: ['Subject to applicable law, users may in particular request:'],
      bullets: [
        'Access to their personal information.',
        'Correction of inaccurate information.',
        'Deletion of information where applicable.',
        'Withdrawal of their consent.',
        'Information about how their data is used and disclosed.',
        'Portability of their data where the law provides for it.',
        'Filing a complaint with the competent authority: {{authority}}.',
      ],
      after: 'Requests may be sent to: {{privacyEmail}}',
    },
    {
      title: '10. Privacy incidents',
      paragraphs: ['In the event of a privacy incident presenting a risk of serious injury, the competent authority and the individuals concerned are notified as soon as possible, in accordance with applicable law. An incident register is kept.'],
    },
    {
      title: '11. Minors',
      paragraphs: ['MizanBI is a professional product intended for organisations and authorised users. It is not designed to be used independently by children.'],
    },
    {
      title: '12. Changes',
      paragraphs: ['This policy may be updated to reflect legal, technical or commercial changes to MizanBI. The date of the latest update is shown at the top of this page.'],
    },
    {
      title: '13. Contact',
      paragraphs: ['For any privacy question: {{privacyEmail}}'],
    },
  ],
}

const TERMS_EN: LegalDoc = {
  title: 'Terms of Use',
  sections: [
    {
      title: '1. Purpose',
      paragraphs: ['These terms set out the rules for accessing and using MizanBI, a Business Intelligence platform that lets organisations connect their data, produce analyses, create visualisations and use artificial-intelligence features.'],
    },
    {
      title: '2. Acceptance',
      paragraphs: [
        'Accessing the platform implies acceptance of these terms. Acceptance is requested at first sign-in and for each new version; it is recorded (account, date and version accepted).',
        'A user who does not accept these terms must stop using the service.',
      ],
    },
    {
      title: '3. Access to the platform',
      paragraphs: ['MizanBI may be offered as a local installation, a deployment on private infrastructure, cloud hosting, or a commercial offer under an annual per-installation licence or subscription. Available features depend on the offer subscribed and the technical configuration.'],
    },
    {
      title: '4. Account creation and security',
      paragraphs: ['The user undertakes to:'],
      bullets: ['Provide accurate information.', 'Protect their credentials.', 'Not share their account without authorisation.', 'Report any unauthorised use.', 'Respect the permissions granted.'],
      after: 'The customer organisation is responsible for managing the users it authorises.',
    },
    {
      title: '5. Authorised use',
      paragraphs: ['The user undertakes to use MizanBI in accordance with applicable law. In particular, it is forbidden to:'],
      bullets: [
        'Use the platform for illegal activities.',
        'Attempt to bypass security mechanisms.',
        'Access other users’ data without authorisation.',
        'Introduce malicious software.',
        'Exploit vulnerabilities of the platform.',
        'Use the service to compromise third-party systems.',
      ],
    },
    {
      title: '6. Data imported by users',
      paragraphs: [
        'The user keeps the rights they hold over the data they import into MizanBI and warrants that they hold the authorisations needed to use it.',
        'MizanBI acquires no ownership of imported data merely by processing it. The provider processes this data only for the purposes authorised by the contract and applicable settings.',
      ],
    },
    {
      title: '7. Artificial intelligence and results',
      paragraphs: ['Results generated by artificial intelligence are provided as analytical assistance. They may contain errors, omissions or incorrect interpretations. The user must verify them before using them for:'],
      bullets: ['Financial decisions.', 'Administrative decisions.', 'Medical decisions.', 'Legal decisions.', 'Important operational decisions.'],
      after: 'MizanBI does not guarantee the absolute accuracy of AI-generated answers.',
    },
    {
      title: '8. Service availability',
      paragraphs: ['Interruptions may occur for maintenance, security, update or technical-failure reasons. Availability, backup, support and recovery terms are defined in the applicable contracts.'],
    },
    {
      title: '9. Intellectual property',
      paragraphs: [
        'Elements specific to MizanBI (code, interface, visual identity, logos, documentation) are protected by applicable intellectual property rights. Any unauthorised reproduction or use is forbidden.',
        'Data belonging to users remains subject to the rights of its respective owners. Open-source components remain subject to their respective licences.',
      ],
    },
    {
      title: '10. Third-party services and public data',
      paragraphs: [
        'Some installations use third-party services or software, subject to their own terms and licences. Their use does not mean their providers are affiliated with MizanBI.',
        'MizanBI includes public or institutional datasets (notably INSTAD, Central Bank of Djibouti, Statistics Canada, CERD, OpenStreetMap) provided for information, with their source stated and under their original licences. These sources do not endorse MizanBI, and their accuracy is not guaranteed.',
      ],
    },
    {
      title: '11. Suspension and termination',
      paragraphs: ['Access may be suspended or terminated in case of serious breach of these terms, fraudulent use, security breach, non-payment where applicable, or legal or regulatory obligation. Terms for data recovery and deletion are defined in the applicable contract.'],
    },
    {
      title: '12. Limitation of liability',
      paragraphs: ['To the extent permitted by applicable law, the provider does not guarantee that analytical or AI-generated results will be error-free. Nothing in these terms is intended to exclude a liability that cannot lawfully be excluded or limited.'],
    },
    {
      title: '13. Changes to the terms',
      paragraphs: ['These terms may be amended to reflect changes to the product, its features or legal obligations. The new version is published on the site and acceptance is requested again.'],
    },
    {
      title: '14. Governing law',
      paragraphs: ['These terms are governed by the following law: {{law}}, subject to mandatory rules applicable to users.'],
    },
    {
      title: '15. Contact',
      paragraphs: ['For any question about these terms: {{contactEmail}}'],
    },
  ],
}

const COOKIES_EN: LegalDoc = {
  title: 'Cookie and Local Storage Policy',
  sections: [
    {
      title: '1. What is a cookie?',
      paragraphs: ['A cookie is a small file stored on a user’s device when they visit a website. A web application can also keep information in the browser’s “local storage” (localStorage and sessionStorage), which plays a comparable role.'],
    },
    {
      title: '2. What MizanBI actually uses',
      paragraphs: ['MizanBI sets no HTTP cookies. It only uses the browser local storage listed below, all strictly necessary for operation or for your preferences:'],
      bullets: [
        'mizan_token (sessionStorage) — your sign-in session token. Removed when the tab is closed or when you sign out.',
        'mizan_email and mizan_user_name (localStorage) — identity shown in the interface. Removed on sign-out.',
        'mizan_theme_mode (localStorage) — your display preference (theme).',
        'mizan_cookie_consent (localStorage) — remembers your cookie choice.',
        'mizan_terms_accepted (localStorage) — remembers the version of the terms of use you accepted.',
        'mizan_ancient_maps_v1 (localStorage) — data you enter in the “Ancient maps” feature. It stays in your browser.',
      ],
    },
    {
      title: '3. What MizanBI does not use',
      bullets: [
        'No analytics cookies and no marketing or advertising cookies.',
        'No third-party trackers.',
        'No third-party service loaded automatically by the browser: map fonts and basemaps are hosted with the application.',
      ],
    },
    {
      title: '4. Consent',
      paragraphs: [
        'The local storage above is strictly necessary: it does not require consent. No optional category is active by default. The instance operator may enable cookieless audience measurement (Plausible or Umami); it then loads only after you accept, and withdrawing your consent stops it.',
        'Refusing non-essential items must not prevent access to essential features.',
      ],
    },
    {
      title: '5. Managing my preferences',
      paragraphs: ['You can change your choice at any time with the “Manage my cookies” button below or in the page footer, and delete local-storage data from your browser settings.'],
    },
    {
      title: '6. Contact',
      paragraphs: ['For any question: {{privacyEmail}}'],
    },
  ],
}

const LEGAL_EN: LegalDoc = {
  title: 'Legal Notice',
  sections: [
    {
      title: 'Publisher',
      bullets: [
        'Publisher: {{company}}',
        'Trade name: MizanBI',
        'Address: {{address}}',
        'Email: {{contactEmail}}',
        'Phone: {{phone}}',
        'Registration number: {{registration}}',
        'Publication manager: {{publisher}}',
      ],
    },
    {
      title: 'Hosting',
      paragraphs: ['{{host}} — region: {{hostRegion}}'],
    },
    {
      title: 'Intellectual property',
      paragraphs: [
        'MizanBI and the original elements of its interface are protected by applicable rights. Third-party components remain subject to their respective licences (see the product’s THIRD_PARTY file).',
        'Mapping and statistical data shown state their source and licence under each map or table (CERD, OpenStreetMap — © OpenStreetMap contributors, ODbL —, INSTAD, Central Bank of Djibouti, Statistics Canada).',
      ],
    },
  ],
}

export const LEGAL_DOCS: Record<Lang, Record<LegalKind, LegalDoc>> = {
  fr: { privacy: PRIVACY_FR, terms: TERMS_FR, cookies: COOKIES_FR, legal: LEGAL_FR },
  en: { privacy: PRIVACY_EN, terms: TERMS_EN, cookies: COOKIES_EN, legal: LEGAL_EN },
}

export function getLegalDoc(kind: LegalKind, lang: Lang): LegalDoc {
  return LEGAL_DOCS[lang][kind]
}

/** Tout le texte d'un document, jetons remplis (sert aux tests et à la détection de placeholders). */
export function legalText(doc: LegalDoc, cfg: LegalConfig = LEGAL): string {
  return doc.sections
    .flatMap(s => [s.title, ...(s.paragraphs ?? []), ...(s.bullets ?? []), ...(s.after ? [s.after] : [])])
    .map(t => fill(t, cfg))
    .join('\n')
}
