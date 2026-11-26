export const commandCenterUrl = "https://atlas-tiger-shield-command-center.imsamtaha-ai.chatgpt.site/";

export const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", ar: "لوحة التحكم", href: "/dashboard" },
  { key: "markets", label: "Markets", ar: "الأسواق", href: commandCenterUrl + "#market" },
  { key: "trade", label: "Paper trader", ar: "التداول الورقي", href: commandCenterUrl + "#trader" },
  { key: "training", label: "Training", ar: "التدريب", href: commandCenterUrl + "#training" },
  { key: "workspace", label: "Saved workspace", ar: "مساحة العمل المحفوظة", href: commandCenterUrl + "#workspace" },
  { key: "discover", label: "Discover", ar: "اكتشف", href: commandCenterUrl + "discover/" },
  { key: "council", label: "TITAN Council", ar: "مجلس تايتن", href: commandCenterUrl + "titan/" },
  { key: "connect", label: "Connections", ar: "الاتصالات", href: "/connect" },
  { key: "account", label: "Account", ar: "الحساب", href: "/login" },
] as const;
