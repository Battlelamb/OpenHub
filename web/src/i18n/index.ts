import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import enCommon from '@/locales/en/common.json'
import enNav from '@/locales/en/nav.json'
import trCommon from '@/locales/tr/common.json'
import trNav from '@/locales/tr/nav.json'

import { en as agentsEn, tr as agentsTr } from './namespaces/agents'
import { en as tasksEn, tr as tasksTr } from './namespaces/tasks'
import { en as workflowsEn, tr as workflowsTr } from './namespaces/workflows'
import { en as dlqEn, tr as dlqTr } from './namespaces/dlq'
import { en as costsEn, tr as costsTr } from './namespaces/costs'
import { en as memoryEn, tr as memoryTr } from './namespaces/memory'
import { en as locksEn, tr as locksTr } from './namespaces/locks'
import { en as healthEn, tr as healthTr } from './namespaces/health'
import { en as settingsEn, tr as settingsTr } from './namespaces/settings'

const browser = typeof navigator !== 'undefined' ? navigator.language.toLowerCase() : 'en'
const initial = browser.startsWith('tr') ? 'tr' : 'en'

i18n.use(initReactI18next).init({
  lng: initial,
  fallbackLng: 'en',
  defaultNS: 'common',
  ns: ['common', 'nav', 'agents', 'tasks', 'workflows', 'dlq', 'costs', 'memory', 'locks', 'health', 'settings'],
  interpolation: { escapeValue: false },
  react: { useSuspense: false },
  resources: {
    en: {
      common: enCommon,
      nav: enNav,
      agents: agentsEn,
      tasks: tasksEn,
      workflows: workflowsEn,
      dlq: dlqEn,
      costs: costsEn,
      memory: memoryEn,
      locks: locksEn,
      health: healthEn,
      settings: settingsEn,
    },
    tr: {
      common: trCommon,
      nav: trNav,
      agents: agentsTr,
      tasks: tasksTr,
      workflows: workflowsTr,
      dlq: dlqTr,
      costs: costsTr,
      memory: memoryTr,
      locks: locksTr,
      health: healthTr,
      settings: settingsTr,
    },
  },
})

export default i18n
