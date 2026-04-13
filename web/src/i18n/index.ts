import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import enCommon from '@/locales/en/common.json'
import enNav from '@/locales/en/nav.json'
import trCommon from '@/locales/tr/common.json'
import trNav from '@/locales/tr/nav.json'

import agentsEn from './namespaces/agents'
import tasksEn from './namespaces/tasks'
import workflowsEn from './namespaces/workflows'
import dlqEn from './namespaces/dlq'
import costsEn from './namespaces/costs'
import memoryEn from './namespaces/memory'
import locksEn from './namespaces/locks'
import healthEn from './namespaces/health'
import settingsEn from './namespaces/settings'

import agentsTr from './namespaces/agents.tr'
import tasksTr from './namespaces/tasks.tr'
import workflowsTr from './namespaces/workflows.tr'
import dlqTr from './namespaces/dlq.tr'
import costsTr from './namespaces/costs.tr'
import memoryTr from './namespaces/memory.tr'
import locksTr from './namespaces/locks.tr'
import healthTr from './namespaces/health.tr'
import settingsTr from './namespaces/settings.tr'

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
