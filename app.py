# Startup Simulation #2 — Assumptions → Experiments → Learning (card-pick, generalized experiment copy)
# Run: streamlit run app_sim2.py

import random
from copy import deepcopy
import streamlit as st

random.seed(17)
st.set_page_config(page_title="Simulation #2: Assumptions → Experiments", page_icon="🧪", layout="wide")

TITLE = "Startup Simulation #2 — Assumptions → Experiments → Learning"

# --------------------------------------------------------------------------------------
# Seed idea (kept for narrative; scoring does not hinge on it directly)
# --------------------------------------------------------------------------------------
SEED_IDEA = {
    "name": "Keep Classes Reliably Full for Independent Gyms",
    "sketch": (
        "You’re exploring a service a typical gym owner could use to keep classes consistently full. "
        "It watches signals (bookings, cancellations, weather, local events) and recommends quick actions "
        "(member swaps, timely promos, partner shares). Target price: $79–$149/month."
    )
}

# --------------------------------------------------------------------------------------
# Assumption catalog (12) — actionable, owner-outcome statements
# --------------------------------------------------------------------------------------
ASSUMPTIONS = [
    {"text":"We can raise fill rate to ≥80% for weekday 2–4pm classes within 14 days.",
     "theme":"Fill Rate", "metric":"Avg fill % (target ≥80%)", "threshold":0.80, "risk":0.90},
    {"text":"At least 25% of trial owners will agree to pay $99/month after a 2-week pilot.",
     "theme":"Price Acceptance", "metric":"Pilot→paid conversion (target ≥25%)", "threshold":0.25, "risk":0.80},
    {"text":"We can acquire the first 10 trial owners at ≤$40 each.",
     "theme":"Acquisition Cost", "metric":"CAC for trial owners (target ≤$40)", "threshold":40, "risk":0.60},
    {"text":"Owners can complete setup in ≤60 minutes without live help.",
     "theme":"Setup Time", "metric":"Time to first use (target ≤60 min)", "threshold":60, "risk":0.65},
    {"text":"Owners will act on ≥70% of our fill prompts in the first 2 weeks.",
     "theme":"Owner Engagement", "metric":"Prompt action rate (target ≥70%)", "threshold":0.70, "risk":0.70},
    {"text":"After value appears, monthly churn will be ≤5%.",
     "theme":"Retention", "metric":"Monthly churn (target ≤5%)", "threshold":0.05, "risk":0.65},
    {"text":"Gross margin can be ≥60% at $99/month.",
     "theme":"Margin", "metric":"Gross margin (target ≥60%)", "threshold":0.60, "risk":0.75},
    {"text":"The approach works for 200+ gyms without response delays.",
     "theme":"Scale", "metric":"On-time suggestion rate at 200+ gyms (target ≥90%)", "threshold":0.90, "risk":0.90},
    {"text":"Local partner studios will share 3–5 empty spots per week.",
     "theme":"Partner Referrals", "metric":"Weekly partner shares (target ≥3)", "threshold":3, "risk":0.55},
    {"text":"New owners will see value (≥10 extra bookings) within 14 days.",
     "theme":"Time-to-Value", "metric":"Extra bookings in 14 days (target ≥10)", "threshold":10, "risk":0.70},
    {"text":"Switching from current process takes ≤30 minutes and 0 data migrations.",
     "theme":"Switching Friction", "metric":"Switch effort (target ≤30 min; no migrations)", "threshold":30, "risk":0.55},
    {"text":"Staff workload will not exceed 3 hours/week per gym.",
     "theme":"Staff Load", "metric":"Ops time per week (target ≤3h)", "threshold":3, "risk":0.60},
]

# Hidden top risks (used for scoring “Risk Prioritization”)
TOP_THEMES = {a["theme"] for a in sorted(ASSUMPTIONS, key=lambda x: x["risk"], reverse=True)[:3]}

# --------------------------------------------------------------------------------------
# Experiments — generalized (non-leading) descriptions
# gain maps = what kinds of assumptions each format tends to de-risk (0..1)
# --------------------------------------------------------------------------------------
EXPERIMENTS = [
    {
        "key":"landing",
        "name":"Landing-page ‘interest’ check",
        "cost":2, "speed":"days",
        "gain":{"Fill Rate":0.5,"Price Acceptance":0.3,"Acquisition Cost":0.3,"Time-to-Value":0.3},
        "do":"Publish a simple value promise and invite prospects to signal interest.",
        "measure":"Impressions, click-through, signups/hand-raises.",
        "decide":"Compare measured rates to simple yardsticks (e.g., CTR <2% weak, >8% strong)."
    },
    {
        "key":"preorder",
        "name":"Commitment (pre-order) test",
        "cost":4, "speed":"weeks",
        "gain":{"Price Acceptance":0.8,"Fill Rate":0.4},
        "do":"Invite a small group to reserve access with a refundable charge.",
        "measure":"Share of invitees who confirm with a card.",
        "decide":"Higher confirm rates indicate real purchase intent (e.g., <5% weak, >12% strong)."
    },
    {
        "key":"concierge",
        "name":"Concierge trial (manual delivery)",
        "cost":3, "speed":"days",
        "gain":{"Fill Rate":0.6,"Owner Engagement":0.5,"Time-to-Value":0.5,"Staff Load":0.3},
        "do":"Manually provide the intended outcome for a tiny cohort over a short period.",
        "measure":"Outcome delta, user follow-through, and your weekly effort.",
        "decide":"If outcomes improve with reasonable effort and users follow through, it’s a strong signal."
    },
    {
        "key":"wizo",
        "name":"‘Looks real’ prototype",
        "cost":3, "speed":"days",
        "gain":{"Setup Time":0.5,"Owner Engagement":0.3,"Staff Load":0.3},
        "do":"Present the intended workflow while handling behind-the-scenes steps manually.",
        "measure":"Completion time and where users stumble or need help.",
        "decide":"Short, mostly self-serve flows are strong; repeated stalls mean redesign."
    },
    {
        "key":"ad_split",
        "name":"Message split test (A/B)",
        "cost":3, "speed":"days",
        "gain":{"Acquisition Cost":0.5,"Fill Rate":0.5},
        "do":"Show two concise messages to the same audience.",
        "measure":"Relative engagement and cost differences.",
        "decide":"Bigger gaps imply a clearer direction; small gaps mean iterate or try new angles."
    },
    {
        "key":"benchmark",
        "name":"Compare to current workaround",
        "cost":2, "speed":"days",
        "gain":{"Time-to-Value":0.4,"Switching Friction":0.5,"Margin":0.3},
        "do":"Run your approach head-to-head with the usual way across a short checklist.",
        "measure":"Wins on time saved, errors avoided, and outcomes.",
        "decide":"More wins = clearer advantage; ties suggest you’re not different enough yet."
    },
    {
        "key":"partner_probe",
        "name":"Quick partner appetite check",
        "cost":1, "speed":"days",
        "gain":{"Partner Referrals":0.7,"Acquisition Cost":0.3},
        "do":"Send a handful of polite outreach notes describing a tiny, specific ask.",
        "measure":"Genuine yeses and concrete offers to try.",
        "decide":"A few earnest yeses justify a deeper test; silence means reframe or pause."
    },
    {
        "key":"ops_interview",
        "name":"Ops & cost chat (lightweight)",
        "cost":1, "speed":"days",
        "gain":{"Margin":0.5,"Staff Load":0.4,"Scale":0.3},
        "do":"Short conversations with operators to map effort, costs, and peak-load risks.",
        "measure":"Ballpark labor and unit costs; steps that won’t scale.",
        "decide":"Healthy margin with no obvious bottleneck is a green light to proceed."
    },
    {
        "key":"scale_drill",
        "name":"Throughput dry-run",
        "cost":2, "speed":"days",
        "gain":{"Scale":0.7,"Owner Engagement":0.2},
        "do":"Simulate higher volume and observe timing/queue behavior.",
        "measure":"On-time rate and backlogs under a larger load.",
        "decide":"High on-time rates suggest headroom; backlogs indicate limits to address."
    },
]

# --------------------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------------------
def init_state():
    st.session_state.s2 = {
        "stage": "intro",     # intro -> pick -> round1 -> results1 -> round2 -> results2 -> (round3) -> score
        "idea": deepcopy(SEED_IDEA),
        "chosen_idx": [],     # indices into ASSUMPTIONS (must be 3)
        "round": 1,
        "tokens": 8,          # round1=8, round2=6, round3=4
        "portfolio": {1:[],2:[],3:[]},   # [{ass_idx, exp_key}]
        "results": {1:[],2:[],3:[]},     # [{ass_idx, exp_key, snippet, pass_band, signal}]
        "learning": {},       # theme -> [0..1]
        "score": None,
        "explanations": {}
    }

if "s2" not in st.session_state:
    init_state()
S = st.session_state.s2

# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def a_quality(text: str) -> float:
    t = text.lower()
    cues = sum(x in t for x in ["≥","≤","%","$"," minutes"," hours"," days"," weeks"," month"," extra"," conversion"])
    return max(0.2, min(1.0, 0.2 + 0.08*cues + 0.015*min(len(t.split()), 36)))

def exp_gain(exp_key, theme):
    exp = next(e for e in EXPERIMENTS if e["key"] == exp_key)
    return exp["gain"].get(theme, 0.0)

def add_learning(theme, signal):
    S["learning"][theme] = min(1.0, S["learning"].get(theme, 0.0) + 0.6*signal)

def decide_band(kind: str, value: float, threshold) -> str:
    if kind in ["Fill Rate","Owner Engagement","Margin","Scale","Time-to-Value"]:
        return "Pass" if value >= threshold else ("Borderline" if value >= threshold*0.9 else "Needs work")
    if kind in ["Price Acceptance"]:
        return "Pass" if value >= threshold else ("Borderline" if value >= threshold*0.75 else "Needs work")
    if kind in ["Acquisition Cost","Setup Time","Switching Friction","Staff Load"]:
        return "Pass" if value <= threshold else ("Borderline" if value <= threshold*1.25 else "Needs work")
    if kind in ["Retention"]:
        return "Pass" if value <= threshold else ("Borderline" if value <= threshold*1.5 else "Needs work")
    if kind in ["Partner Referrals"]:
        return "Pass" if value >= threshold else ("Borderline" if value >= max(1, threshold-1) else "Needs work")
    return "—"

def synth_result(exp_key: str, ass_idx: int):
    a = ASSUMPTIONS[ass_idx]
    theme = a["theme"]
    quality = a_quality(a["text"])
    base = exp_gain(exp_key, theme)
    steer = 1.15 if theme in TOP_THEMES else 1.0
    signal = base * (0.6 + 0.4*quality) * steer

    # Generate values appropriate to the metric and craft a snippet
    if theme == "Fill Rate":
        val = max(0.55, min(0.95, 0.65 + 0.35*signal + random.uniform(-0.05,0.05)))
        band = decide_band(theme, val, a["threshold"])
        snippet = f"Measured average fill: **{val*100:.0f}%** (target ≥80%). **Decision:** {band}."
        return snippet, band, signal
    if theme == "Price Acceptance":
        val = max(0.02, min(0.50, 0.05 + 0.45*signal + random.uniform(-0.03,0.03)))
        band = decide_band(theme, val, a["threshold"])
        snippet = f"Pilot→paid conversion: **{val*100:.1f}%** (target ≥25%). **Decision:** {band}."
        return snippet, band, signal
    if theme == "Acquisition Cost":
        val = max(15, min(120, 90 - 70*signal + random.uniform(-8,8)))
        band = decide_band(theme, val, a["threshold"])
        snippet = f"Estimated CAC: **${val:.0f}** (target ≤$40). **Decision:** {band}."
        return snippet, band, signal
    if theme == "Setup Time":
        val = max(20, min(180, 130 - 90*signal + random.uniform(-10,10)))
        band = decide_band(theme, val, a["threshold"])
        snippet = f"Time to complete setup: **{val:.0f} min** (target ≤60). **Decision:** {band}."
        return snippet, band, signal
    if theme == "Owner Engagement":
        val = max(0.30, min(0.95, 0.45 + 0.5*signal + random.uniform(-0.08,0.08)))
        band = decide_band(theme, val, a["threshold"])
        snippet = f"Prompt action rate: **{val*100:.0f}%** (target ≥70%). **Decision:** {band}."
        return snippet, band, signal
    if theme == "Retention":
        val = max(0.01, min(0.20, 0.15 - 0.12*signal + random.uniform(-0.02,0.02)))
        band = decide_band(theme, val, a["threshold"])
        snippet = f"Projected monthly churn: **{val*100:.1f}%** (target ≤5%). **Decision:** {band}."
        return snippet, band, signal
    if theme == "Margin":
        val = max(0.35, min(0.85, 0.45 + 0.45*signal + random.uniform(-0.05,0.05)))
        band = decide_band(theme, val, a["threshold"])
        snippet = f"Estimated gross margin: **{val*100:.0f}%** (target ≥60%). **Decision:** {band}."
        return snippet, band, signal
    if theme == "Scale":
        val = max(0.60, min(0.98, 0.75 + 0.25*signal + random.uniform(-0.06,0.04)))
        band = decide_band(theme, val, a["threshold"])
        snippet = f"On-time suggestions at 200 gyms: **{val*100:.0f}%** (target ≥90%). **Decision:** {band}."
        return snippet, band, signal
    if theme == "Partner Referrals":
        val = max(0, min(10, int(1 + 8*signal + random.uniform(-1,1))))
        band = decide_band(theme, val, a["threshold"])
        snippet = f"Positive partner replies: **{val}/10** (target ≥3). **Decision:** {band}."
        return snippet, band, signal
    if theme == "Time-to-Value":
        val = max(0, min(25, int(3 + 20*signal + random.uniform(-2,2))))
        band = decide_band(theme, val, a["threshold"])
        snippet = f"Extra bookings in 14 days: **{val}** (target ≥10). **Decision:** {band}."
        return snippet, band, signal
    if theme == "Switching Friction":
        val = max(5, min(120, 90 - 70*signal + random.uniform(-8,8)))
        band = decide_band(theme, val, a["threshold"])
        snippet = f"Switch time: **{val:.0f} min** (target ≤30; no migrations). **Decision:** {band}."
        return snippet, band, signal
    if theme == "Staff Load":
        val = max(0.5, min(8.0, 6.5 - 5.5*signal + random.uniform(-0.5,0.5)))
        band = decide_band(theme, val, a["threshold"])
        snippet = f"Ops time per gym: **{val:.1f} h/week** (target ≤3h). **Decision:** {band}."
        return snippet, band, signal

    return "Result captured.", "—", signal

# --------------------------------------------------------------------------------------
# Scoring + explanations
# --------------------------------------------------------------------------------------
def compute_score_and_explanations():
    # Risk prioritization: did Round 1 include top themes?
    r1_themes = [ASSUMPTIONS[i["ass_idx"]]["theme"] for i in S["portfolio"][1]]
    hits = len([t for t in r1_themes if t in TOP_THEMES])
    prioritization = hits / max(1, len(S["portfolio"][1]))

    # Experiment fit: average exp->theme gain across all runs
    fits = []
    for rnd in [1,2,3]:
        for it in S["portfolio"][rnd]:
            theme = ASSUMPTIONS[it["ass_idx"]]["theme"]
            fits.append(exp_gain(it["exp_key"], theme))
    exp_fit = sum(fits)/len(fits) if fits else 0.0

    # Resource efficiency: start scrappy and iterate
    costs = []
    for rnd in [1,2,3]:
        c = 0
        for it in S["portfolio"][rnd]:
            c += next(e for e in EXPERIMENTS if e["key"]==it["exp_key"])["cost"]
        costs.append(c)
    resource = 1.0
    if costs and costs[0] > 6: resource -= 0.2
    if len(S["portfolio"][2]) == 0: resource -= 0.2
    resource = max(0.0, resource)

    # Learning outcome: themes with learning > 0.55
    learned = sum(1 for v in S["learning"].values() if v > 0.55)
    learning = learned / max(1, len(S["learning"]) or 1)

    # Assumption quality: specificity of the 3 chosen
    aq = sum(a_quality(ASSUMPTIONS[i]["text"]) for i in S["chosen_idx"])/max(1, len(S["chosen_idx"]) or 1)

    total = round(100*(0.28*prioritization + 0.27*exp_fit + 0.20*resource + 0.15*learning + 0.10*aq))
    S["score"] = {
        "total": total,
        "components":{
            "Risk Prioritization": round(prioritization,2),
            "Experiment Fit": round(exp_fit,2),
            "Resource Efficiency": round(resource,2),
            "Learning Outcome": round(learning,2),
            "Assumption Quality": round(aq,2),
        }
    }

    # Build explanations (why each score looks the way it does)
    expl = {}
    # Risk Prioritization
    if hits >= 2:
        expl["Risk Prioritization"] = (
            f"You tested {hits} of the 3 highest-risk themes in Round 1 "
            f"({', '.join(sorted(TOP_THEMES))}). That’s strong prioritization."
        )
    elif hits == 1:
        expl["Risk Prioritization"] = (
            f"You hit 1 of the top 3 risks in Round 1. Consider swapping in another top risk earlier."
        )
    else:
        expl["Risk Prioritization"] = (
            "Round 1 missed the riskiest themes. Start with the few uncertainties that could kill the idea."
        )

    # Experiment Fit
    if exp_fit >= 0.7:
        expl["Experiment Fit"] = (
            "Your chosen tests typically yield strong signals for the themes you targeted—good matching."
        )
    elif exp_fit >= 0.5:
        expl["Experiment Fit"] = (
            "Fit was mixed. Some choices were solid; others could be replaced by formats that produce clearer signals."
        )
    else:
        expl["Experiment Fit"] = (
            "Low fit. Re-map each assumption to a test that directly demonstrates the behavior you care about."
        )

    # Resource Efficiency
    r1 = costs[0] if costs else 0
    ran_r2 = len(S["portfolio"][2]) > 0
    if resource >= 0.9:
        expl["Resource Efficiency"] = (
            f"Good pacing. Round 1 spent {r1} tokens and you left room to iterate (Round 2 {'ran' if ran_r2 else 'did not run'})."
        )
    else:
        msg = []
        if r1 > 6: msg.append(f"Round 1 was heavy at {r1} tokens")
        if not ran_r2: msg.append("no Round 2 experiments")
        expl["Resource Efficiency"] = " and ".join(msg) or "Token use can be lighter in Round 1."

    # Learning Outcome
    if learning >= 0.7:
        expl["Learning Outcome"] = (
            f"You built strong learning in multiple themes (≥0.55 coverage). Nice breadth without losing depth."
        )
    elif learning >= 0.4:
        expl["Learning Outcome"] = (
            "Some themes reached clear learning; consider extending to the next most critical area."
        )
    else:
        expl["Learning Outcome"] = (
            "Few themes crossed the confidence bar. Consider lower-cost tests to widen coverage sooner."
        )

    # Assumption Quality
    if aq >= 0.75:
        expl["Assumption Quality"] = (
            "Your assumptions were specific and measurable—easy to call with data."
        )
    elif aq >= 0.55:
        expl["Assumption Quality"] = (
            "Assumptions were partially specific. Add thresholds (%, counts, time) to sharpen decisions."
        )
    else:
        expl["Assumption Quality"] = (
            "Assumptions were broad. Rephrase to observable behaviors with explicit thresholds."
        )

    S["explanations"] = expl

# --------------------------------------------------------------------------------------
# UI Blocks
# --------------------------------------------------------------------------------------
def header():
    st.title(TITLE)
    st.caption("Pick the riskiest assumptions, run scrappy experiments, and make clear calls using simple yardsticks.")

def block_intro():
    st.subheader("What you’ll do")
    st.markdown("""
**First you will** pick **three** assumptions (from twelve) that feel riskiest for a typical gym owner.  
**Then you will** choose low-cost experiments (with tokens) and **run Round 1**.  
**Next you will** review results with **Pass / Borderline / Needs work** calls and decide Round 2 (and optional Round 3).  
**Finally you will** get a score, reasons for each component, and coaching notes.

Time guide: ~45–60 minutes total.
""")
    if st.button("Start", key="start"):
        S["stage"] = "pick"; st.rerun()

def block_pick():
    st.subheader("Pick your top three assumptions to test")
    st.info(f"Seed idea: **{SEED_IDEA['name']}** — {SEED_IDEA['sketch']}")
    st.markdown("_Click exactly three boxes below._")

    cols = st.columns(3)
    chosen = []
    for i, a in enumerate(ASSUMPTIONS):
        with cols[i%3]:
            st.checkbox(
                f"**{a['text']}**  \n_{a['theme']}_  \n• Metric: {a['metric']}",
                key=f"a_{i}"
            )
            if st.session_state.get(f"a_{i}"):
                chosen.append(i)

    st.write(f"Selected: **{len(chosen)}/3**")
    if len(chosen) != 3:
        st.warning("Please select exactly three assumptions.")
    else:
        if st.button("Confirm & go to Round 1", key="to_r1"):
            S["chosen_idx"] = chosen
            S["stage"] = "round1"
            S["round"] = 1
            S["tokens"] = 8
            st.rerun()

# ---- Experiment card renderer (general wording, non-leading) -------------------------
def render_exp_card(exp, round_idx, ass_idx):
    with st.container(border=True):
        st.markdown(f"**{exp['name']}**  \n_{exp['speed']} • cost {exp['cost']} tokens_")
        st.markdown(
            f"**What it is:** {exp['do']}  \n"
            f"**Signals you’ll see:** {exp['measure']}  \n"
            f"**How to judge:** {exp['decide']}"
        )
        if st.button(f"Add — cost {exp['cost']}", key=f"btn_{round_idx}_{ass_idx}_{exp['key']}"):
            add_to_portfolio(round_idx, ass_idx, exp['key'])

def block_round(round_idx:int):
    st.subheader(f"Round {round_idx}: pick a portfolio of experiments")
    st.write(f"Tokens available: **{S['tokens']}**")

    for ass_idx in S["chosen_idx"]:
        a = ASSUMPTIONS[ass_idx]
        with st.expander(f"{a['text']}  —  _{a['theme']}_  | Metric: {a['metric']}", expanded=False):
            cols = st.columns(3)
            for j, exp in enumerate(EXPERIMENTS):
                with cols[j % 3]:
                    render_exp_card(exp, round_idx, ass_idx)

    if S["portfolio"][round_idx]:
        st.markdown("#### Selected this round")
        for n, it in enumerate(S["portfolio"][round_idx], start=1):
            a = ASSUMPTIONS[it["ass_idx"]]
            e = next(e for e in EXPERIMENTS if e["key"]==it["exp_key"])
            st.write(f"{n}. **{a['text']}** → **{e['name']}** (cost {e['cost']})")

    left, right = st.columns(2)
    left.button("Run experiments",
                disabled=(len(S["portfolio"][round_idx])==0),
                key=f"run_{round_idx}",
                on_click=lambda: run_round(round_idx))
    if round_idx > 1:
        right.button("Skip to scoring", key=f"skip_{round_idx}", on_click=lambda: to_score())

def add_to_portfolio(round_idx:int, ass_idx:int, exp_key:str):
    exp = next(e for e in EXPERIMENTS if e["key"]==exp_key)
    if exp["cost"] > S["tokens"]:
        st.toast("Not enough tokens for that experiment.", icon="⚠️")
        return
    S["tokens"] -= exp["cost"]
    S["portfolio"][round_idx].append({"ass_idx": ass_idx, "exp_key": exp_key})
    st.rerun()

def run_round(round_idx:int):
    S["results"][round_idx] = []
    for it in S["portfolio"][round_idx]:
        snippet, band, signal = synth_result(it["exp_key"], it["ass_idx"])
        S["results"][round_idx].append({**it, "snippet":snippet, "pass_band":band, "signal":signal})
        theme = ASSUMPTIONS[it["ass_idx"]]["theme"]
        add_learning(theme, signal)
    S["stage"] = f"results{round_idx}"
    st.rerun()

def block_results(round_idx:int):
    st.subheader(f"Round {round_idx} results")
    for r in S["results"][round_idx]:
        a = ASSUMPTIONS[r["ass_idx"]]
        e = next(e for e in EXPERIMENTS if e["key"]==r["exp_key"])
        color = "🟢" if r["pass_band"]=="Pass" else ("🟠" if r["pass_band"]=="Borderline" else "🔴")
        st.success(f"{color} **{a['theme']}** — {e['name']}  \n{r['snippet']}")

    st.markdown("#### Learning coverage (by theme)")
    if S["learning"]:
        for k,v in S["learning"].items():
            st.write(f"- {k}: {v:.2f}")
    else:
        st.write("No learning recorded yet.")

    left, right = st.columns(2)
    if round_idx == 1:
        left.button("Plan Round 2", key="to_r2",
                    on_click=lambda: go_round(2, tokens=6))
        right.button("Skip to scoring", key="skip1", on_click=lambda: to_score())
    elif round_idx == 2:
        left.button("Plan Round 3 (optional)", key="to_r3",
                    on_click=lambda: go_round(3, tokens=4))
        right.button("Skip to scoring", key="skip2", on_click=lambda: to_score())
    else:
        left.button("Compute score", key="to_score", on_click=lambda: to_score())

def go_round(idx:int, tokens:int):
    S["stage"] = f"round{idx}"
    S["round"] = idx
    S["tokens"] = tokens
    st.rerun()

def to_score():
    S["stage"] = "score"
    compute_score_and_explanations()
    st.rerun()

def block_score():
    if S["score"] is None:
        compute_score_and_explanations()
    st.subheader("Score and coaching")
    st.metric("Total Score", f"{S['score']['total']}/100")

    st.markdown("#### Category scores (with reasons)")
    for k,v in S["score"]["components"].items():
        label = "Excellent" if v>=0.8 else ("Good" if v>=0.6 else "Needs work")
        st.write(f"- **{k}:** {int(v*100)}/100 — {label}")
        st.caption(S["explanations"].get(k,""))

    st.markdown("#### Coaching notes")
    st.write("**1) Start with the few uncertainties that could kill the idea.** Make Round 1 a bet on those, not on nice-to-know items.")
    st.write("**2) Match the format to the decision.** If you need real purchase intent, use a commitment test; if you need behavioral proof, use a short manual trial; if you need message clarity, split test your message.")
    st.write("**3) Decide with thresholds, not vibes.** Set pass/borderline/fail bars up front (%, counts, time). Call the result and state the next step.")
    st.write("**4) Spend lightly to earn iteration.** Use inexpensive tests first so you can pivot or double-down in Round 2 without running out of tokens.")
    st.write("**5) Capture a specific next test.** Every result should end with a clear follow-up (format, metric, threshold, and what you’ll do in each outcome).")

    if st.button("Restart simulation", key="restart"):
        init_state(); st.rerun()

# --------------------------------------------------------------------------------------
# Flow
# --------------------------------------------------------------------------------------
def main():
    header()
    stage = S["stage"]
    if stage == "intro":
        block_intro()
    elif stage == "pick":
        block_pick()
    elif stage == "round1":
        block_round(1)
    elif stage == "results1":
        block_results(1)
    elif stage == "round2":
        block_round(2)
    elif stage == "results2":
        block_results(2)
    elif stage == "round3":
        block_round(3)
    elif stage == "results3":
        block_results(3)
    else:
        block_score()

main()
