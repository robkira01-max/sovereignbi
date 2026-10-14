export type Locale = 'ar' | 'en' | 'es'
export const SUPPORTED_LOCALES: Locale[] = ['ar', 'en', 'es']
export const DEFAULT_LOCALE: Locale = 'en'

export const LOCALE_LABELS: Record<Locale, string> = {
  ar: 'AR',
  en: 'EN',
  es: 'ES',
}

type DeepRecord = { [k: string]: DeepRecord | string }

const translations: Record<Locale, DeepRecord> = {
  ar: {
    nav: {
      chat: 'دردشة',
      dashboards: 'لوحات البيانات',
      import: 'استيراد',
      logout: 'تسجيل الخروج',
    },
    login: {
      title: 'SovereignBI — تسجيل الدخول',
      api_key: 'مفتاح API',
      submit: 'دخول',
      key_required: 'الرجاء إدخال مفتاح API.',
    },
    chat: {
      title: 'الدردشة التحليلية',
      placeholder: 'مثال: ما هو إجمالي الإيرادات حسب المنطقة؟',
      submit: 'إرسال',
      answer: 'الإجابة',
      sql: 'SQL',
      results: 'النتائج ({n} صفوف)',
      error_unknown: 'خطأ غير معروف',
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
      chat: 'Chat',
      dashboards: 'Dashboards',
      import: 'Import',
      logout: 'Logout',
    },
    login: {
      title: 'SovereignBI — Login',
      api_key: 'API Key',
      submit: 'Login',
      key_required: 'Please enter an API key.',
    },
    chat: {
      title: 'Analytical Chat',
      placeholder: 'E.g.: What is the total revenue by region?',
      submit: 'Submit',
      answer: 'Answer',
      sql: 'SQL',
      results: 'Results ({n} rows)',
      error_unknown: 'Unknown error',
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
      title: 'Dashboards',
      no_dashboards: 'No dashboards.',
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
      chat: 'Chat',
      dashboards: 'Paneles',
      import: 'Importar',
      logout: 'Cerrar sesión',
    },
    login: {
      title: 'SovereignBI — Inicio de sesión',
      api_key: 'Clave API',
      submit: 'Iniciar sesión',
      key_required: 'Por favor ingrese una clave API.',
    },
    chat: {
      title: 'Chat analítico',
      placeholder: 'Ej.: ¿Cuál es el ingreso total por región?',
      submit: 'Enviar',
      answer: 'Respuesta',
      sql: 'SQL',
      results: 'Resultados ({n} filas)',
      error_unknown: 'Error desconocido',
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
      title: 'Paneles',
      no_dashboards: 'No hay paneles.',
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
