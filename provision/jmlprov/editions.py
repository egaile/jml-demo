"""What each edition builds. Rules not listed for an edition are not created on that site."""
SECRET_RULES = ["A2 Joiner day one", "A7 Badge deactivation", "Demo reset", "Demo: teams done"]   # created DISABLED: secrets are pasted in the UI

EDITIONS = {
    "atlassian": {
        "label": "Atlassian edition: Jira Automation rules, Rovo agents, Time to SLA",
        "apps": ["Time to SLA (Appfire)"],
        "automation": ["A1 Joiner fan-out", "A2 Joiner day one", "A3 Mover revoke before grant", "A4 Mover advances", "A5 Leaver countdown",
                       "A5b Manager confirmation received", "A6 Leaver fan-out", "A7 Badge deactivation", "A8 Leaver verified",
                       "A9 SLA breach escalation", "A10 Link agent tasks", "Demo reset", "Demo: teams done"],
        "automation_fallback": [],     # created but left DISABLED (another mechanism does the job)
        "jmwe": False, "dashboard_hub": False,
    },
    "appfire": {
        "label": "Appfire edition: JMWE post-functions and actions, Dashboard Hub Pro reporting, Time to SLA; Automation keeps the integrations",
        "apps": ["Time to SLA (Appfire)", "Jira Misc Workflow Extensions, JMWE (Appfire)", "Dashboard Hub Pro (Appfire)"],
        "automation": ["A2 Joiner day one", "A7 Badge deactivation", "A9 SLA breach escalation", "Demo reset", "Demo: teams done",
                       "A5 Leaver countdown", "A5b Manager confirmation received", "A10 Link agent tasks"],
        "automation_fallback": ["A5 Leaver countdown", "A5b Manager confirmation received", "A10 Link agent tasks"],   # JMWE actions replace them once configured in the JMWE UI
        "jmwe": True, "dashboard_hub": True,
    },
}
