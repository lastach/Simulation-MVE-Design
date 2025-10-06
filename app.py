# Startup Simulation #2 — Assumptions → Experiments → Learning (Streamlit, no tabs)
# -----------------------------------------------------------------------
# Run: streamlit run app_sim2.py
# Deploy on Streamlit Cloud with main file path = app_sim2.py
# -----------------------------------------------------------------------

import random
from copy import deepcopy
import streamlit as st

random.seed(17)
st.set_page_config(page_title="Simulation #2: Assumptions → Experiments", page_icon="🧪", layout="wide")

TITLE = "Startup Simulation #2 — Assumptions → Experiments → Learning"

# -------------------------- Seed idea & ground truth --------------------------
SEED_IDEA = {
    "name": "Stabilize Class Occupancy for Independent Gyms",
    "sketch": (
        "You are exploring a service that helps independent gyms keep classes consistently full. "
        "The approach: monitor signals (bookings, cancellations, weather, local events) and suggest quick fill tactics "
        "(member swaps, timely offers, partner referrals). The pricing under consideration is a monthly subscription "
        "in the $79–$149 range."
    )
}

# We remove the D/F/V lens. Instead we model hidden risk by assumption THEME.
THEMES = [
    "Demand", "Willingness to Pay", "Acquisition", "Delivery Capacity", "Data Access",
    "Automation", "Churn", "Margin", "Scale", "Partners", "Time-to-Value", "Switching Cost"
]

# Curated assumption candidates (12). Each has a hidden risk (0..1) and theme.
ASSUMPTION_CATALOG = [
    {"text":"At least 15% of targeted visitors will join a waitlist in one week.", "theme":"Demand", "risk":0.85},
    {"text":"10% of contacted gym owners will pre-order at $99/mo.", "theme":"Willingness to Pay", "risk":0.80},
    {"text":"We can acquire qualified owners for <$25 each with simple ads.", "theme":"Acquisition", "risk":0.55},
    {"text":"We can act on demand signals fast enough to fill mid-week gaps.", "theme":"Delivery Capacity", "risk":0.70},
    {"text":"We can get the booking + cancellations data we need from most gyms.", "theme":"Data Access", "risk":0.90},
    {"text":"≥70% of fill suggestions can be executed without human intervention.", "theme":"Automation", "risk":0.75},
    {"text":"If value is delivered, monthly churn will be ≤5%.", "theme":"Churn", "risk":0.65},
    {"text":"Gross margin will be ≥60% at $99/mo with <4 hours/week of ops.", "theme":"Margin", "risk":0.75},
    {"text":"The approach still works for 200+ gyms without response delays.", "theme":"Scale", "risk":0.90},
    {"text":"Local studios will agree to cross-promote each other’s empty spots.", "theme":"Partners", "risk":0.60},
    {"text":"New gyms will see clear value within 14 days of signup.", "theme":"Time-to-Value", "risk":0.70},
    {"text":"Studios can adopt the service without process disruption.", "theme":"Switching Cost", "risk":0.55},
]

# Hidden “top risks” (inform scoring)
TOP_RISKS = sorted(ASSUMPTION_CATALOG, key=lambda a: a["risk"], reverse=True)[:3]  # 3 highest risk items

# -------------------------- Experiment catalog --------------------------
EXPERIMENTS = [
    {"key":"landing_page","name":"Landing page / smoke test","cost":2,"speed":"days",
     "gain":{"Demand":0.7,"Willingness to Pay":0.3,"Acquisition":0.3},
     "desc":"Drive targeted traffic to a simple value proposition and measure conversions.",
     "bench":"CTR yardsticks: <2% weak • 2–5% fair • 5–8% promising • >8% strong"},
    {"key":"concierge_mvp","name":"Concierge MVP","cost":3,"speed":"days",
     "gain":{"Delivery Capacity":0.6,"Time-to-Value":0.4,"Churn":0.3},
     "desc":"Manually deliver the outcome for a handful of customers to test behavior.",
     "bench":"Repurchase yardsticks: 0–1 weak • 2–3 fair • 4+ strong (out of 6–8 trials)"},
    {"key":"wizard_of_oz","name":"Wizard-of-Oz prototype","cost":3,"speed":"days",
     "gain":{"Automation":0.6,"Delivery Capacity":0.4},
     "desc":"UI appears automated; human performs the backend steps to prove flow.",
     "bench":"Automation yardsticks: <50% tasks automated weak • 50–70% fair • >70% strong"},
    {"key":"preorder","name":"Pre-order / crowdfunding","cost":4,"speed":"weeks",
     "gain":{"Willingness to Pay":0.8,"Demand":0.4},
     "desc":"Collect real purchase intent before full build.",
     "bench":"Buy rate yardsticks: <5% weak • 5–12% fair • >12% strong (from warm leads)"},
    {"key":"expert_interview","name":"Expert interview","cost":1,"speed":"days",
     "gain":{"Data Access":0.4,"Scale":0.3,"Margin":0.3},
     "desc":"Pressure-test plan with seasoned operators (data sources, costs, risks).",
     "bench":"Use to refine assumptions; not a pass/fail signal alone."},
    {"key":"benchmark","name":"Benchmark vs. workaround","cost":2,"speed":"days",
     "gain":{"Time-to-Value":0.4,"Switching Cost":0.5,"Margin":0.3},
     "desc":"Compare against current hacks (spreadsheets, manual outreach).",
     "bench":"Win count out of 10 criteria: <5 weak • 5–7 fair • 8+ strong"},
    {"key":"ad_split","name":"Ad split test","cost":3,"speed":"days",
     "gain":{"Demand":0.6,"Acquisition":0.4},
     "desc":"Test two messages to see which resonates with the same audience.",
     "bench":"CTR gap yardsticks: <0.5pp weak • 0.5–1.5pp fair • >1.5pp strong"},
    {"key":"diary_study","name":"Diary study / usage log","cost":2,"speed":"weeks",
     "gain":{"Demand":0.3,"Time-to-Value":0.3,"Churn":0.3},
     "desc":"Have target users log pain occurrences for 1–2 weeks.",
     "bench":"Frequent, repeated pain across entries is a strong signal"},
    {"key":"partner_probe","name":"Partner probe","cost":1,"speed":"days",
     "gain":{"Partners":0.6,"Acquisition":0.3},
     "desc":"Quick outreach to gauge willingness of local studios to cross-promote.",
     "bench":"Positive replies yardsticks: <2 weak • 2–4 fair • 5+ strong (out of ~10 warm pings)"}
]

# -------------------------- State --------------------------
def init_state():
    st.session_state.s2 = {
        "stage": "intro",           # intro -> pick -> round1 -> results1 -> round2 -> results2 -> round3 -> score
        "idea": deepcopy(SEED_IDEA),
        "chosen": [],               # list of chosen assumptions
        "round": 1,
        "tokens": 8,                # round1=8, round2=6, round3=4
        "portfolio": {1:[],2:[],3:[]},     # selected experiments [{assumption_idx, exp_key}]
        "results": {1:[],2:[],3:[]},       # results per round
        "learning": {},             # per theme cumulative learning 0..1
        "score": None
    }

def theme_gain(exp_key, theme):
    exp = next(e for e in EXPERIMENTS if e["key"]==exp_key)
    return exp["gain"].get(theme, 0.0)

def assumption_quality_from_text(txt:str)->float:
    t = txt.lower()
    cues = sum(x in t for x in ["%","$"," per "," within "," days"," week"," month"," buy"," pre-order"," waitlist"])
    length = len(t.split())
    return max(0.2, min(1.0, 0.2 + 0.1*cues + 0.02*min(length, 30)))

def synth_result(exp_key, assumption):
    """Semi-random snippet biased by exp->theme gain and the assumption's hidden risk; produce interpretation."""
    exp = next(e for e in EXPERIMENTS if e["key"]==exp_key)
    theme = assumption["theme"]
    base = exp["gain"].get(theme, 0.0)
    # If theme is among top hidden risks, slightly stronger noise-weight
    top_themes = {a["theme"] for a in TOP_RISKS}
    steer = 1.15 if theme in top_themes else 1.0
    quality = assumption_quality_from_text(assumption["text"])
    signal = base * (0.6 + 0.4*quality) * steer

    if exp_key=="landing_page":
        imps = random.randint(320, 900)
        ctr = max(0.5, min(14.0, 2.0 + 11.0*signal + random.uniform(-1.2,1.2)))
        verdict = "weak" if ctr<2 else ("fair" if ctr<5 else ("promising" if ctr<8 else "strong"))
        return (f"Landing page: {imps} impressions → CTR **{ctr:.1f}%** "
                f"(est. waitlist signups ≈ **{int(imps*ctr/100*0.6)}**). "
                f"**Interpretation:** {verdict}. {exp['bench']}"), signal

    if exp_key=="ad_split":
        headline_A = "Keep mid-week classes full with timely fills"
        headline_B = "Reduce empty spots and stabilize weekly revenue"
        a = max(0.4, min(10.0, 1.2 + 8.5*signal + random.uniform(-1.0,1.0)))
        b = max(0.3, min(9.0, 0.9 + 8.0*(signal-0.08) + random.uniform(-1.0,1.0)))
        diff = abs(a-b); win = "A" if a>b else "B"
        verdict = "weak" if diff<0.5 else ("fair" if diff<1.5 else "strong")
        return (f"Ad split:\n- A “{headline_A}” → **{a:.1f}%**\n- B “{headline_B}” → **{b:.1f}%**\n"
                f"Winner: **{win}** (gap {diff:.1f}pp). **Interpretation:** {verdict}. {exp['bench']}"), signal

    if exp_key=="preorder":
        leads = random.randint(10, 30)
        conv = max(0.0, min(0.35, 0.05 + 0.38*signal + random.uniform(-0.05,0.05)))
        buys = max(0, int(leads*conv))
        verdict = "weak" if conv<0.05 else ("fair" if conv<0.12 else "strong")
        return (f"Pre-order: {leads} leads → **{buys}** confirmed cards "
                f"({conv*100:.1f}% buy). **Interpretation:** {verdict}. {exp['bench']}"), signal

    if exp_key=="concierge_mvp":
        trials = random.randint(6, 8)
        repurchase = max(0, int(trials*(0.18 + 0.60*signal + random.uniform(-0.1,0.1))))
        verdict = "weak" if repurchase<=1 else ("fair" if repurchase<=3 else "strong")
        return (f"Concierge trial: {trials} customers → **{repurchase}** would pay again. "
                f"**Interpretation:** {verdict}. {exp['bench']}"), signal

    if exp_key=="wizard_of_oz":
        tasks = random.randint(18, 32)
        auto = int(tasks*(0.48 + 0.45*signal + random.uniform(-0.1,0.1)))
        pct = 100*auto/max(tasks,1)
        verdict = "weak" if pct<50 else ("fair" if pct<70 else "strong")
        return (f"Wizard-of-Oz: automated **{auto}/{tasks}** tasks (**{pct:.0f}%**). "
                f"**Interpretation:** {verdict}. {exp['bench']}"), signal

    if exp_key=="expert_interview":
        insights = 2 + int(4*signal + random.uniform(0,2))
        return (f"Expert interview: **{insights}** actionable takeaways. "
                f"**Interpretation:** directional; refine assumptions. {exp['bench']}"), signal*0.6

    if exp_key=="benchmark":
        win = max(3, int(10*signal + random.uniform(-1,2)))
        verdict = "weak" if win<5 else ("fair" if win<8 else "strong")
        return (f"Benchmark vs workaround: won **{win}/10** criteria. "
                f"**Interpretation:** {verdict}. {exp['bench']}"), signal

    if exp_key=="diary_study":
        entries = 6 + int(5*signal + random.uniform(0,3))
        return (f"Diary study: **{entries}** entries. Repeated pain: "
                f"“inconsistent mid-week demand”. **Interpretation:** recurring pain is strong evidence."), signal*0.7

    if exp_key=="partner_probe":
        replies = max(0, int(10*(0.15 + 0.6*signal + random.uniform(-0.1,0.1))))
        verdict = "weak" if replies<2 else ("fair" if replies<5 else "strong")
        return (f"Partner probe: **{replies}/10** positive replies to cross-promote. "
                f"**Interpretation:** {verdict}. {exp['bench']}"), signal

    return "Result pending", signal

def add_learning(theme, signal):
    S = st.session_state.s2
    cur = S["learning"].get(theme, 0.0)
    S["learning"][theme] = min(1.0, cur + 0.6*signal)

# -------------------------- Scoring --------------------------
def compute_score():
    S = st.session_state.s2
    # Prioritization: how many of the true top risks were included in Round 1 picks?
    round1_themes = [S["chosen"][it["assumption_idx"]]["theme"] for it in S["portfolio"][1]]
    top_themes = {a["theme"] for a in TOP_RISKS}
    hits = len([t for t in round1_themes if t in top_themes])
    prioritization = hits / min(3, len(S["portfolio"][1]) or 1)

    # Experiment Fit: avg exp gain for that assumption's theme
    fits = []
    for rnd in [1,2,3]:
        for it in S["portfolio"][rnd]:
            a = S["chosen"][it["assumption_idx"]]
            fits.append(theme_gain(it["exp_key"], a["theme"]))
    exp_fit = (sum(fits)/len(fits)) if fits else 0.0

    # Resource Efficiency: start low-cost and leave tokens for iteration
    costs = [sum(next(e for e in EXPERIMENTS if e["key"]==it["exp_key"])["cost"]
                 for it in S["portfolio"][rnd]) for rnd in [1,2,3]]
    resource = 1.0
    if costs and costs[0] > 6:
        resource -= 0.2
    if len(S["portfolio"][2]) == 0:
        resource -= 0.2
    resource = max(0.0, resource)

    # Learning Outcome: how many distinct themes reached decent learning?
    learned = sum(1 for v in S["learning"].values() if v > 0.55)
    learning = learned / max(1, len(S["learning"]))

    # Assumption Coverage Quality: specificity proxy of chosen assumptions
    aq = sum(assumption_quality_from_text(a["text"]) for a in S["chosen"]) / max(1, len(S["chosen"]))

    total = round(100*(0.25*prioritization + 0.25*exp_fit + 0.20*resource + 0.20*learning + 0.10*aq))
    S["score"] = {
        "total": total,
        "components": {
            "Risk Prioritization": round(prioritization,2),
            "Experiment Fit": round(exp_fit,2),
            "Resource Efficiency": round(resource,2),
            "Learning Outcome": round(learning,2),
            "Assumption Quality": round(aq,2),
        }
    }

# -------------------------- UI Blocks --------------------------
def header():
    st.title(TITLE)
    st.caption("Objective: surface hidden assumptions, pick scrappy experiments, and maximize validated learning per unit of effort.")

def block_intro():
    st.subheader("What you’ll do")
    st.markdown("""
**First you will** pick your top **3 assumptions** (from a short list).  
**Then you will** choose quick, low-cost experiments to test them (with token constraints).  
**Next you will** run the experiments, see data snippets with yardsticks, and iterate.  
**Finally you will** get a score and coaching notes.
""")
    if st.button("Start", key="start"):
        st.session_state.s2["stage"] = "pick"
        st.rerun()

def block_pick_assumptions():
    st.subheader("Pick your top 3 assumptions to test")
    st.info(f"Seed idea: **{SEED_IDEA['name']}** — {SEED_IDEA['sketch']}")
    options = [f"{i+1}. {a['text']}  —  _{a['theme']}_" for i,a in enumerate(ASSUMPTION_CATALOG)]
    idxs = st.multiselect("Choose exactly 3 assumptions that feel riskiest for this idea:",
                          options=list(range(len(options))), format_func=lambda i: options[i], max_selections=3, key="pick_idxs")
    if len(idxs) != 3:
        st.warning("Please select exactly 3.")
    else:
        st.session_state.s2["chosen"] = [ASSUMPTION_CATALOG[i] for i in idxs]
        col1, col2, col3 = st.columns([1,1,1])
        if col2.button("Confirm & go to Round 1", key="to_r1"):
            S = st.session_state.s2
            S["stage"] = "round1"
            S["round"] = 1
            S["tokens"] = 8
            st.rerun()

def block_round(round_idx:int):
    S = st.session_state.s2
    st.subheader(f"Round {round_idx}: pick a portfolio of experiments")
    st.write(f"Tokens available: **{S['tokens']}**")
    # chooser
    a_opts = [f"{i+1}. {a['text']}  —  _{a['theme']}_" for i,a in enumerate(S["chosen"])]
    c1, c2 = st.columns(2)
    a_idx = c1.selectbox("Choose an assumption", list(range(len(a_opts))), format_func=lambda i: a_opts[i], key=f"a_{round_idx}")
    exp = c2.selectbox("Choose an experiment", EXPERIMENTS, format_func=lambda e: f"{e['name']} (cost {e['cost']})", key=f"e_{round_idx}")
    st.caption(f"About this experiment: {exp['desc']}  \n**Benchmarks:** {exp['bench']}")

    if st.button("Add to portfolio", key=f"add_{round_idx}"):
        cost = exp["cost"]
        if cost > S["tokens"]:
            st.error("Not enough tokens for that experiment.")
        else:
            S["tokens"] -= cost
            S["portfolio"][round_idx].append({"assumption_idx": a_idx, "exp_key": exp["key"]})
            st.rerun()

    if S["portfolio"][round_idx]:
        st.markdown("#### Selected this round")
        for n,item in enumerate(S["portfolio"][round_idx], start=1):
            a = S["chosen"][item["assumption_idx"]]
            e = next(x for x in EXPERIMENTS if x["key"]==item["exp_key"])
            st.write(f"{n}. **{a['text']}**  (_{a['theme']}_ ) → **{e['name']}** (cost {e['cost']})")

    cL, cR = st.columns(2)
    if cL.button("Run experiments", disabled=(len(S["portfolio"][round_idx])==0), key=f"run_{round_idx}"):
        S["results"][round_idx] = []
        for item in S["portfolio"][round_idx]:
            a = S["chosen"][item["assumption_idx"]]
            snippet, signal = synth_result(item["exp_key"], a)
            S["results"][round_idx].append({"assumption":a, "exp_key":item["exp_key"], "snippet":snippet, "signal":signal})
            add_learning(a["theme"], signal)
        S["stage"] = f"results{round_idx}"
        st.rerun()

def block_results(round_idx:int):
    S = st.session_state.s2
    st.subheader(f"Round {round_idx} results")
    for r in S["results"][round_idx]:
        st.success(f"- **{r['assumption']['text']}**  (_{r['assumption']['theme']}_ )\n\n{r['snippet']}")
    st.markdown("#### Learning coverage (by theme)")
    if S["learning"]:
        for k,v in S["learning"].items():
            st.write(f"- {k}: {v:.2f}")
    else:
        st.write("No learning recorded yet.")

    cols = st.columns(2)
    if round_idx == 1:
        if cols[0].button("Plan Round 2", key="to_r2"):
            S["stage"] = "round2"
            S["round"] = 2
            S["tokens"] = 6
            st.rerun()
        if cols[1].button("Skip to scoring", key="skip1"):
            S["stage"] = "score"; compute_score(); st.rerun()
    elif round_idx == 2:
        if cols[0].button("Plan Round 3 (optional)", key="to_r3"):
            S["stage"] = "round3"
            S["round"] = 3
            S["tokens"] = 4
            st.rerun()
        if cols[1].button("Skip to scoring", key="skip2"):
            S["stage"] = "score"; compute_score(); st.rerun()
    else:
        if cols[0].button("Compute score", key="to_score"):
            S["stage"] = "score"; compute_score(); st.rerun()

def block_score():
    S = st.session_state.s2
    if S["score"] is None:
        compute_score()
    st.subheader("Score and feedback")
    st.metric("Total Score", f"{S['score']['total']}/100")

    st.markdown("#### Category scores")
    for k,v in S["score"]["components"].items():
        label = ("Excellent" if v>=0.8 else "Good" if v>=0.6 else "Needs work")
        st.write(f"- **{k}:** {int(v*100)}/100 — {label}")

    st.markdown("#### Coaching notes")
    st.write("- **Prioritize the true riskiest items first.** Don’t spend tokens on nice-to-know tests.")
    st.write("- **Match the test to the assumption.** Use pre-orders for price/commitment; concierge or Wizard-of-Oz for delivery/automation; landing/ad tests for demand and message.")
    st.write("- **Use yardsticks.** Interpret numbers versus benchmarks—not in isolation.")
    st.write("- **Iterate deliberately.** Use Round 1 results to pivot, double-down, or move to the next critical assumption.")
    st.write("- **Capture a clear next step.** Each result should produce a validate/invalidate takeaway and your next test.")

    if st.button("Restart simulation", key="restart"):
        init_state(); st.rerun()

# -------------------------- App flow --------------------------
if "s2" not in st.session_state:
    init_state()

S = st.session_state.s2
header()

stage = S["stage"]
if stage == "intro":
    block_intro()
elif stage == "pick":
    block_pick_assumptions()
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
