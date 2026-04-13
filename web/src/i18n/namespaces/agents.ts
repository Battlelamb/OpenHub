export const en = {
  title: "Agents",
  columns: { name: "Name", status: "Status", capabilities: "Capabilities", lastSeen: "Last seen", currentTask: "Current task" },
  emptyHeading: "No agents registered",
  emptyBody: "Connect an agent via scripts/run_bridge.py or POST /v1/agents.",
  status: { online: "online", offline: "offline", idle: "idle", error: "error" },
} as const
export const tr = {
  title: "Ajanlar",
  columns: { name: "Ad", status: "Durum", capabilities: "Yetenekler", lastSeen: "Son gorulme", currentTask: "Aktif gorev" },
  emptyHeading: "Kayitli ajan yok",
  emptyBody: "scripts/run_bridge.py ile bir ajan bagla veya POST /v1/agents cagir.",
  status: { online: "online", offline: "offline", idle: "idle", error: "hata" },
} as const
