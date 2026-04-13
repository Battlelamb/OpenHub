import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import enCommon from '@/locales/en/common.json'
import enNav from '@/locales/en/nav.json'
import trCommon from '@/locales/tr/common.json'
import trNav from '@/locales/tr/nav.json'

const browser = typeof navigator !== 'undefined' ? navigator.language.toLowerCase() : 'en'
const initial = browser.startsWith('tr') ? 'tr' : 'en'

i18n.use(initReactI18next).init({
  lng: initial,
  fallbackLng: 'en',
  defaultNS: 'common',
  ns: ['common', 'nav'],
  interpolation: { escapeValue: false },
  react: { useSuspense: false },
  resources: {
    en: { common: enCommon, nav: enNav },
    tr: { common: trCommon, nav: trNav },
  },
})

export default i18n
