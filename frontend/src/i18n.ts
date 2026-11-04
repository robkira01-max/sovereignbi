export type Locale = 'fr' | 'ar' | 'en' | 'es'
export const SUPPORTED_LOCALES: Locale[] = ['fr', 'en', 'ar', 'es']
export const DEFAULT_LOCALE: Locale = 'fr'

export const LOCALE_LABELS: Record<Locale, string> = {
  fr: 'FR',
  ar: 'AR',
  en: 'EN',
  es: 'ES',
}

type DeepRecord = { [k: string]: DeepRecord | string }

const translations: Record<Locale, DeepRecord> = {
  fr: {
    nav: {
      home: 'Accueil',
      chat: 'Q&A',
      dashboards: 'Rapports',
      import: 'Données',
      logout: 'Déconnexion',
    },
    login: {
      title: 'MizanBI — Connexion',
      subtitle: 'BI conversationnelle souveraine',
      email: 'Email',
      password: 'Mot de passe',
      error: 'Identifiants incorrects.',
      fields_required: 'Email et mot de passe requis.',
      api_key: 'Clé API',
      submit: 'Connexion',
      key_required: 'Veuillez entrer une clé API.',
    },
    home: {
      welcome: 'Bonjour 👋',
      subtitle: 'Que voulez-vous analyser aujourd\'hui ?',
      action_chat: 'Poser une question',
      action_chat_desc: 'Interrogez vos données en langage naturel',
      action_dashboard: 'Rapports',
      action_dashboard_desc: 'Visualisez et partagez vos tableaux de bord',
      action_upload: 'Importer des données',
      action_upload_desc: 'Ajoutez un fichier CSV, Excel ou connectez une base',
      data_sources: 'Sources de données',
      add_source: 'Ajouter',
      no_data: 'Aucune donnée connectée. Importez un fichier pour commencer.',
    },
    chat: {
      title: 'Q&A analytique',
      placeholder: 'Ex. : Quel est le total des ventes par région ? Ou posez n\'importe quelle question.',
      submit: 'Envoyer',
      answer: 'Réponse',
      sql: 'SQL',
      results: 'Résultats ({n} lignes)',
      error_unknown: 'Erreur inconnue',
      empty_hint: 'Posez une question — sur vos données ou tout autre sujet.',
      clear: 'Effacer',
      mode_data: 'Analyser les données',
      mode_badge_data: '📊 Données',
      mode_badge_general: '💬 Général',
    },
    upload: {
      title: 'Importer des données',
      format_error: 'Formats acceptés : CSV, XLSX, XLSM',
      loading: 'Chargement…',
      drop_hint: 'Glissez un fichier CSV / XLSX ou cliquez pour sélectionner',
      tables_loaded: 'Tables chargées :',
      error_upload: 'Erreur lors de l\'import',
    },
    dashboard: {
      title: 'Rapports',
      no_dashboards: 'Aucun rapport.',
      back: '← Retour',
      saving: 'Enregistrement…',
      add_tile: '+ Tuile',
      id_label: 'ID',
      title_label: 'Titre',
      type_label: 'Type',
      add: 'Ajouter',
      cancel: 'Annuler',
      drag_hint: 'Faites glisser les tuiles pour les réorganiser.',
      delete_tile: 'Supprimer la tuile',
      no_tiles: 'Aucune tuile. Cliquez sur « + Tuile » pour en ajouter une.',
      tile_id_placeholder: 'ex. : kpi_total',
      tile_title_placeholder: 'ex. : Total des ventes',
    },
    confidence: {
      label: 'Confiance :',
      high: 'élevée',
      medium: 'moyenne',
      low: 'faible',
    },
    sql: {
      copy: 'Copier',
      copied: 'Copié !',
    },
    tile: {
      unknown: 'Type de tuile inconnu :',
    },
  },

  ar: {
    nav: {
      home: 'الرئيسية',
      chat: 'دردشة',
      dashboards: 'لوحات البيانات',
      import: 'البيانات',
      logout: 'تسجيل الخروج',
    },
    login: {
      title: 'MizanBI — تسجيل الدخول',
      subtitle: 'تحليل بيانات ذكي وسيادي',
      email: 'البريد الإلكتروني',
      password: 'كلمة المرور',
      error: 'بيانات الاعتماد غير صحيحة.',
      fields_required: 'البريد الإلكتروني وكلمة المرور مطلوبان.',
      api_key: 'مفتاح API',
      submit: 'دخول',
      key_required: 'الرجاء إدخال مفتاح API.',
    },
    home: {
      welcome: 'مرحباً 👋',
      subtitle: 'ماذا تريد أن تحلل اليوم؟',
      action_chat: 'اطرح سؤالاً',
      action_chat_desc: 'استعلم عن بياناتك بلغة طبيعية',
      action_dashboard: 'التقارير',
      action_dashboard_desc: 'عرض لوحات البيانات ومشاركتها',
      action_upload: 'استيراد البيانات',
      action_upload_desc: 'أضف ملف CSV أو Excel',
      data_sources: 'مصادر البيانات',
      add_source: 'إضافة',
      no_data: 'لا توجد بيانات. استورد ملفاً للبدء.',
    },
    chat: {
      title: 'الدردشة التحليلية',
      placeholder: 'مثال: ما هو إجمالي الإيرادات حسب المنطقة؟',
      submit: 'إرسال',
      answer: 'الإجابة',
      sql: 'SQL',
      results: 'النتائج ({n} صفوف)',
      error_unknown: 'خطأ غير معروف',
      empty_hint: 'اطرح سؤالاً — حول البيانات أو أي موضوع آخر.',
      clear: 'مسح',
      mode_data: 'تحليل البيانات',
      mode_badge_data: '📊 بيانات',
      mode_badge_general: '💬 عام',
    },
    upload: {
      title: 'استيراد البيانات',
      format_error: 'الصيغ المقبولة: CSV, XLSX, XLSM',
      loading: 'جارٍ التحميل…',
      drop_hint: 'اسحب ملف CSV / XLSX أو انقر للتحديد',
      tables_loaded: 'الجداول المحملة:',
      error_upload: 'خطأ في الرفع',
    },
    dashboard: {
      title: 'لوحات البيانات',
      no_dashboards: 'لا توجد لوحات بيانات.',
      back: 'رجوع →',
      saving: 'جارٍ الحفظ…',
      add_tile: '+ بطاقة',
      id_label: 'المعرف',
      title_label: 'العنوان',
      type_label: 'النوع',
      add: 'إضافة',
      cancel: 'إلغاء',
      drag_hint: 'اسحب البطاقات لإعادة ترتيبها.',
      delete_tile: 'حذف البطاقة',
      no_tiles: 'لا بطاقات. انقر على «+ بطاقة» لإضافة واحدة.',
      tile_id_placeholder: 'مثال: kpi_total',
      tile_title_placeholder: 'مثال: إجمالي المبيعات',
    },
    confidence: {
      label: 'الثقة:',
      high: 'عالية',
      medium: 'متوسطة',
      low: 'منخفضة',
    },
    sql: {
      copy: 'نسخ',
      copied: 'تم النسخ!',
    },
    tile: {
      unknown: 'نوع بطاقة غير معروف:',
    },
  },

  en: {
    nav: {
      home: 'Home',
      chat: 'Q&A',
      dashboards: 'Reports',
      import: 'Data',
      logout: 'Logout',
    },
    login: {
      title: 'MizanBI — Login',
      subtitle: 'Sovereign conversational BI',
      email: 'Email',
      password: 'Password',
      error: 'Invalid credentials.',
      fields_required: 'Email and password are required.',
      api_key: 'API Key',
      submit: 'Login',
      key_required: 'Please enter an API key.',
    },
    home: {
      welcome: 'Welcome 👋',
      subtitle: 'What would you like to analyse today?',
      action_chat: 'Ask a question',
      action_chat_desc: 'Query your data in natural language',
      action_dashboard: 'Reports',
      action_dashboard_desc: 'View and share your dashboards',
      action_upload: 'Import data',
      action_upload_desc: 'Add a CSV, Excel file or connect a database',
      data_sources: 'Data sources',
      add_source: 'Add',
      no_data: 'No data connected. Import a file to get started.',
    },
    chat: {
      title: 'Analytical Q&A',
      placeholder: 'E.g.: What is the total revenue by region? Or ask anything.',
      submit: 'Send',
      answer: 'Answer',
      sql: 'SQL',
      results: 'Results ({n} rows)',
      error_unknown: 'Unknown error',
      empty_hint: 'Ask a question — about your data or anything else.',
      clear: 'Clear',
      mode_data: 'Analyse data',
      mode_badge_data: '📊 Data',
      mode_badge_general: '💬 General',
    },
    upload: {
      title: 'Import Data',
      format_error: 'Accepted formats: CSV, XLSX, XLSM',
      loading: 'Loading…',
      drop_hint: 'Drop a CSV / XLSX file or click to select',
      tables_loaded: 'Loaded tables:',
      error_upload: 'Upload error',
    },
    dashboard: {
      title: 'Reports',
      no_dashboards: 'No reports.',
      back: '← Back',
      saving: 'Saving…',
      add_tile: '+ Tile',
      id_label: 'ID',
      title_label: 'Title',
      type_label: 'Type',
      add: 'Add',
      cancel: 'Cancel',
      drag_hint: 'Drag tiles to reorder.',
      delete_tile: 'Delete tile',
      no_tiles: 'No tiles. Click "+ Tile" to add one.',
      tile_id_placeholder: 'e.g.: kpi_total',
      tile_title_placeholder: 'e.g.: Total sales',
    },
    confidence: {
      label: 'Confidence:',
      high: 'high',
      medium: 'medium',
      low: 'low',
    },
    sql: {
      copy: 'Copy',
      copied: 'Copied!',
    },
    tile: {
      unknown: 'Unknown tile type:',
    },
  },

  es: {
    nav: {
      home: 'Inicio',
      chat: 'Q&A',
      dashboards: 'Informes',
      import: 'Datos',
      logout: 'Cerrar sesión',
    },
    login: {
      title: 'MizanBI — Inicio de sesión',
      subtitle: 'BI conversacional soberana',
      email: 'Correo electrónico',
      password: 'Contraseña',
      error: 'Credenciales incorrectas.',
      fields_required: 'Correo y contraseña son requeridos.',
      api_key: 'Clave API',
      submit: 'Iniciar sesión',
      key_required: 'Por favor ingrese una clave API.',
    },
    home: {
      welcome: 'Bienvenido 👋',
      subtitle: '¿Qué desea analizar hoy?',
      action_chat: 'Hacer una pregunta',
      action_chat_desc: 'Consulte sus datos en lenguaje natural',
      action_dashboard: 'Informes',
      action_dashboard_desc: 'Visualice y comparta sus paneles',
      action_upload: 'Importar datos',
      action_upload_desc: 'Agregue un archivo CSV, Excel o conecte una BD',
      data_sources: 'Fuentes de datos',
      add_source: 'Agregar',
      no_data: 'Sin datos conectados. Importe un archivo para empezar.',
    },
    chat: {
      title: 'Chat analítico',
      placeholder: 'Ej.: ¿Cuál es el ingreso total por región? O pregunta lo que quieras.',
      submit: 'Enviar',
      answer: 'Respuesta',
      sql: 'SQL',
      results: 'Resultados ({n} filas)',
      error_unknown: 'Error desconocido',
      empty_hint: 'Haz una pregunta — sobre tus datos o cualquier tema.',
      clear: 'Limpiar',
      mode_data: 'Analizar datos',
      mode_badge_data: '📊 Datos',
      mode_badge_general: '💬 General',
    },
    upload: {
      title: 'Importar datos',
      format_error: 'Formatos aceptados: CSV, XLSX, XLSM',
      loading: 'Cargando…',
      drop_hint: 'Arrastra un archivo CSV / XLSX o haz clic para seleccionar',
      tables_loaded: 'Tablas cargadas:',
      error_upload: 'Error de carga',
    },
    dashboard: {
      title: 'Informes',
      no_dashboards: 'No hay informes.',
      back: '← Volver',
      saving: 'Guardando…',
      add_tile: '+ Mosaico',
      id_label: 'ID',
      title_label: 'Título',
      type_label: 'Tipo',
      add: 'Agregar',
      cancel: 'Cancelar',
      drag_hint: 'Arrastre los mosaicos para reordenarlos.',
      delete_tile: 'Eliminar mosaico',
      no_tiles: 'No hay mosaicos. Haga clic en "+ Mosaico" para agregar uno.',
      tile_id_placeholder: 'p.ej.: kpi_total',
      tile_title_placeholder: 'p.ej.: Total ventas',
    },
    confidence: {
      label: 'Confianza:',
      high: 'alta',
      medium: 'media',
      low: 'baja',
    },
    sql: {
      copy: 'Copiar',
      copied: '¡Copiado!',
    },
    tile: {
      unknown: 'Tipo de mosaico desconocido:',
    },
  },
}

export function getTranslation(locale: Locale, key: string): string {
  const parts = key.split('.')
  let node: DeepRecord | string = translations[locale]
  for (const p of parts) {
    if (typeof node !== 'object' || !(p in node)) return key
    node = node[p]
  }
  return typeof node === 'string' ? node : key
}

export function tplStr(str: string, vars: Record<string, string | number>): string {
  return str.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? `{${k}}`))
}

export function getAllKeys(locale: Locale, prefix = ''): string[] {
  const keys: string[] = []
  const obj = prefix
    ? prefix.split('.').reduce((acc: DeepRecord | string, p) => {
        if (typeof acc !== 'object') return acc
        return acc[p] as DeepRecord | string
      }, translations[locale] as DeepRecord | string)
    : translations[locale]

  if (typeof obj !== 'object') return keys
  for (const k of Object.keys(obj)) {
    const full = prefix ? `${prefix}.${k}` : k
    const val = (obj as DeepRecord)[k]
    if (typeof val === 'string') keys.push(full)
    else keys.push(...getAllKeys(locale, full))
  }
  return keys
}
