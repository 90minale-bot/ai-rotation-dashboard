# ======================================================
# AI ROI TRACKER KEYWORD LISTS
# Built for AI earnings commentary:
# NVDA, MSFT, META, AMD, AVGO
# ======================================================


# ======================================================
# POSITIVE AI MOMENTUM SIGNALS
# Phase 1: Buildout / Expansion
# ======================================================

POSITIVE_AI_TERMS = {
    # Explicit AI demand
    "strong ai demand": 4,
    "robust ai demand": 4,
    "accelerating ai demand": 5,
    "continued strong demand for ai": 4,
    "ai demand exceeded expectations": 5,
    "ai demand outstripping supply": 5,
    "broad-based ai demand": 4,
    "durable ai demand": 4,
    "structural ai demand": 4,

    # NVIDIA / hyperscaler / data center language
    "data center demand": 3,
    "strong data center demand": 4,
    "data center growth": 3,
    "record data center revenue": 5,
    "data center revenue": 3,
    "data center segment revenue": 3,
    "accelerated computing": 4,
    "compute demand": 3,
    "compute growth": 3,
    "compute equals revenue": 5,
    "ai infrastructure": 4,
    "ai infrastructure demand": 4,
    "ai infrastructure investment": 4,
    "ai infrastructure company": 4,
    "training workloads": 3,
    "inference workloads": 3,
    "agentic ai": 4,
    "ai factories": 4,

    # GPU / architecture demand
    "gpu demand": 3,
    "strong gpu demand": 4,
    "increasing gpu deployments": 3,
    "accelerating gpu deployments": 4,
    "blackwell": 4,
    "blackwell adoption": 5,
    "blackwell demand": 5,
    "rubin": 3,
    "h100 demand": 5,
    "h200 demand": 5,
    "gb200": 4,
    "gb300": 4,

    # Capacity / supply / backlog
    "capacity commitments": 4,
    "supply commitments": 4,
    "inventory and supply commitments": 5,
    "long-term supply agreements": 5,
    "multi-year demand": 5,
    "multi-year opportunity": 4,
    "visibility into demand": 4,
    "line of sight": 4,
    "backlog growth": 4,
    "record backlog": 5,
    "ai backlog": 4,

    # Investment expansion
    "increased ai investment": 4,
    "accelerating ai investment": 5,
    "investing aggressively in ai": 5,
    "continued ai infrastructure investment": 4,
    "expanding ai capacity": 4,
    "capacity expansion for ai": 4,
    "data center expansion": 3,
    "ai data center expansion": 4,
    "hyperscale ai buildout": 5,
    "higher ai capex": 4,
    "capex driven by ai": 4,
    "capital expenditures driven by ai": 4,
    "ai remains a top investment priority": 4,

    # Microsoft / cloud / Copilot / Azure language
    "azure ai": 4,
    "azure ai services": 4,
    "ai services growth": 4,
    "copilot usage": 3,
    "growing copilot usage": 4,
    "m365 copilot": 3,
    "github copilot": 3,
    "ai capacity constraints": 3,
    "continued investments in ai": 4,
    "investments in ai": 3,
    "ai cloud demand": 4,
    "cloud ai demand": 4,

    # Meta / model / infrastructure language
    "ai infrastructure costs": 2,
    "ai infrastructure buildout": 4,
    "generative ai products": 3,
    "llama": 3,
    "recommendation ai": 3,
    "ai-driven engagement": 4,
    "ai improves engagement": 4,
    "ai ranking": 3,
    "ai-powered advertising": 4,
    "ai ad tools": 4,

    # AMD / Instinct / EPYC language
    "epyc": 3,
    "instinct gpu": 4,
    "instinct gpus": 4,
    "instinct adoption": 4,
    "instinct revenue": 4,
    "mi300": 4,
    "mi308": 3,
    "mi325": 4,
    "mi350": 5,
    "mi450": 5,
    "rocm": 3,
    "data center ai franchise": 5,
    "rapid scaling of our data center ai franchise": 5,
    "record instinct gpu revenue": 5,
    "hyperscalers expanded": 4,
    "production workloads": 5,

    # Broadcom / custom silicon / networking language
    "custom ai accelerators": 5,
    "ai accelerators": 4,
    "custom ai silicon": 5,
    "xpu": 4,
    "ai networking": 5,
    "custom ai processors": 5,
    "ai semiconductor revenue": 5,
    "ai revenue growth is accelerating": 5,
    "robust demand for custom ai accelerators": 5,
    "robust demand for custom ai accelerators and ai networking": 6,
    "ethernet for ai": 4,
    "spectrum-x": 4,
    "infiniband": 3,

    # Adoption / monetization
    "ai adoption increasing": 4,
    "enterprise ai adoption": 3,
    "ai adoption accelerating": 5,
    "production ai deployments": 5,
    "ai moving into production": 5,
    "ai-driven revenue": 5,
    "ai revenue growth": 5,
    "generative ai demand": 4,
    "strong bookings for ai": 4,
    "ai workloads growing": 4,
    "workloads growing": 3,

    # Strategic confidence language
    "early innings of ai": 3,
    "long runway for ai growth": 4,
    "multi-year ai opportunity": 4,
    "sustained ai growth": 4,
    "customers are racing to invest": 5,
    "customers racing to invest": 5,
    "future demand": 4,
}


# ======================================================
# TRANSITION / OPTIMIZATION SIGNALS
# Phase 2: ROI Scrutiny / Efficiency / Utilization
# These are not automatically bearish. They often mean the AI cycle is maturing.
# ======================================================

NEUTRAL_AI_TERMS = {
    # ROI awareness
    "ai roi": 3,
    "measuring ai roi": 3,
    "evaluating ai roi": 3,
    "return on ai investment": 3,
    "ai payback period": 3,
    "time to value": 3,
    "proof of value": 3,
    "business value from ai": 3,

    # Optimization language
    "optimization phase": 3,
    "optimization of ai spend": 3,
    "optimizing ai infrastructure": 3,
    "optimizing gpu utilization": 3,
    "improving utilization": 3,
    "utilization improving": 3,
    "ai efficiency": 3,
    "efficiency over expansion": 3,
    "balancing growth and efficiency": 3,
    "cost optimization": 3,
    "cost reductions": 2,
    "performance improvements and cost reductions": 3,

    # Deployment transition
    "transitioning to deployment": 3,
    "shift from buildout to utilization": 4,
    "moving from training to inference": 3,
    "focus on inference": 3,
    "scaling inference": 3,
    "from pilots to production": 3,
    "moving into production": 3,

    # Budget discipline
    "disciplined ai spending": 3,
    "selective ai investment": 3,
    "targeted ai investment": 3,
    "prioritizing high-return ai projects": 3,
    "phased ai deployment": 3,
    "capital discipline": 3,
    "investment discipline": 3,

    # Margin / cost management that may be normal
    "efficiency gains": 2,
    "partially offset by continued investments in ai": 2,
    "partially offset by investments in ai": 2,
    "operating efficiency": 2,
}


# ======================================================
# NEGATIVE AI ROI / SLOWDOWN SIGNALS
# Phase 3: Slowdown / ROI Disappointment / Demand Weakness
# ======================================================

NEGATIVE_AI_ROI_TERMS = {
    # Direct ROI breakdown
    "uncertain ai returns": 5,
    "poor ai roi": 6,
    "weak ai roi": 6,
    "ai roi concerns": 5,
    "concerns around ai roi": 5,
    "difficulty monetizing ai": 5,
    "ai monetization concerns": 5,
    "lack of ai monetization": 6,
    "ai monetization slower than expected": 6,
    "ai payback period lengthening": 5,
    "return on ai investment remains unclear": 6,

    # Spending slowdown
    "slower ai spending": 5,
    "ai spending slowdown": 5,
    "pause in ai investment": 6,
    "pausing ai investment": 6,
    "reduced ai capex": 5,
    "lower ai capex": 5,
    "cutting ai spending": 6,
    "ai budget cuts": 6,
    "delayed ai projects": 5,
    "deferring ai investment": 5,
    "pulling back on ai spend": 6,
    "slowing ai investments": 5,
    "ai investments slowing": 5,

    # Capacity digestion
    "capacity digestion": 6,
    "digesting capacity": 6,
    "digesting ai capacity": 6,
    "gpu digestion": 6,
    "gpu utilization below expectations": 6,
    "underutilized gpu capacity": 6,
    "underutilized capacity": 5,
    "excess ai capacity": 6,
    "oversupply of ai capacity": 6,
    "inventory digestion": 5,
    "data center capacity digestion": 6,
    "slower data center buildout": 5,

    # Demand weakening
    "softening ai demand": 5,
    "moderating ai demand": 4,
    "ai demand normalization": 5,
    "pullback in ai demand": 5,
    "ai demand slowing": 6,
    "ai demand slowed": 6,
    "lower ai demand": 6,
    "weaker ai demand": 6,
    "ai backlog declining": 6,
    "ai order growth slowing": 5,

    # Enterprise hesitation
    "customers delaying ai projects": 5,
    "customers delaying deployments": 5,
    "longer sales cycles for ai": 4,
    "slower deal conversion": 4,
    "ai budget pressure": 5,
    "increased scrutiny on ai spend": 5,
    "customer scrutiny increased": 4,
    "customers are cautious": 3,
    "macro uncertainty impacting ai": 4,

    # Regulatory / geopolitical AI risk
    "export restrictions": 4,
    "regulatory approvals": 3,
    "china regulatory": 4,
    "china restrictions": 4,
    "unable to ship to china": 5,
    "china-based customers": 3,

    # Competition / substitution risk
    "competition from chinese companies": 4,
    "custom chips reducing reliance": 4,
    "reducing reliance on nvidia": 5,
    "in-house ai chips": 4,
    "ai chip competition": 4,

    # Margin / cost pressure
    "ai margin pressure": 4,
    "gpu costs weighing on margins": 4,
    "higher ai costs": 3,
    "ai infrastructure costs elevated": 3,
    "cost of ai remains high": 3,
    "ai capex weighing on free cash flow": 4,
    "ai investments pressuring margins": 4,

    # Bubble / skepticism
    "ai bubble": 4,
    "overinvestment in ai": 5,
    "ai spending bubble": 5,
    "questioning ai returns": 5,
    "investors questioning ai roi": 6,
}