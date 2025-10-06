# Startup Simulation #2 — Assumptions → Experiments → Learning (Streamlit)
# -----------------------------------------------------------------------
# Run locally:  streamlit run app_sim2.py
# Deploy on Streamlit Cloud with main file path = app_sim2.py
# -----------------------------------------------------------------------

import random
from copy import deepcopy
import streamlit as st
import streamlit.components.v1 as components

random.seed(17)

st.set_page_config(page_title="Simulation #2: Assumptions → Experiments", page_icon="🧪", layout="wide")
TITLE = "Startup Simulation #2 — Assumptions → Experiments → Learning"

# -------------------------- Seed idea & ground truth (hidden) --------------------------
SEED_IDEA = {
    "name": "Stabilize Class Occupancy for Independent Gyms",
    "sketch": (
        "You are exploring a service that helps independent gyms keep classes consistently full. "
        "The idea is to watch demand signals (bookings, cancellations, weather, local events) and "
        "suggest quick fill tactics (swap members, send timely offers, leverage partner referrals). "
        "Pricing under consideration: a monthly subscription in the $79–$149 range."
    )
}

# Hidden “truth” map (guides noisy outcomes). Each bucket has a top risk emphasis.
GROUND_TRUTH = {
    "desirability": {"willing_to_pay": 0.6, "real_problem": 0.9, "findability": 0.5},
    "feasibility":  {"ops_capacity": 0.7, "tooling_speed": 0.5, "data_access": 0.8},
    "viability":    {"unit_economics": 0.8, "churn_risk": 0.7, "scalability": 0.9},
    "top": {"desirability":"real_problem", "feasibility":"data_access", "viability":"scalability"}
}

# -------------------------- Experiment catalog --------------------------
EXPERIMENTS = [
    {"key":"landing_page","name":"Landing page / smoke test","cost":2,"speed":"days",
     "gain":{"desirability":0.6,"feasibility":0.0,"viability":0.2},
     "desc":"Drive targeted traffic to a simple value proposition and measure conversions.",
     "bench":"CTR yardsticks: <2% weak • 2–5% fair • 5–8% promising • >8% strong"},
    {"key":"concierge_mvp","name":"Concierge MVP","cost":3,"speed":"days",
     "gain":{"desirability":0.4,"feasibility":0.5,"viability":0.2},
     "desc":"Manually deliver the outcome for a handful of customers to test behavior.",
     "bench":"Repurchase yardsticks: 0–1 weak • 2–3 fair • 4+ strong (out of 6–8 trials)"},
    {"key":"wizard_of_oz","name":"Wizard-of-Oz prototype","cost":3,"speed":"days",
     "gain":{"desirability":0.2,"feasibility":0.6,"viability":0.1},
     "desc":"UI appears automated; human performs the backend steps to prove flow.",
     "bench":"Automation yardsticks: <50% tasks automated weak • 50–70% fair • >70% strong"},
    {"key":"preorder","name":"Pre-order / crowdfunding","cost":4,"speed":"weeks",
     "gain":{"desirability":0.8,"feasibility":0.0,"viability":0.3},
     "desc":"Collect real purchase intent before full build.",
     "bench":"Buy rate yardsticks: <5% weak • 5–12% fair • >12% strong (from warm leads)"},
    {"key":"expert_interview","name":"Expert interview","cost":1,"speed":"days",
     "gain":{"desirability":0.2,"feasibility":0.2,"viability":0.2},
     "desc":"Pressure-test plan with seasoned operators.",
     "bench":"Use to refine assumptions; not a pass/fail signal alone."},
    {"key":"benchmark","name":"Benchmark vs. workaround","cost":2,"speed":"days",
     "gain":{"desirability":0.3,"feasibility":0.2,"viability":0.3},
     "desc":"Compare against current hacks (e.g., spreadsheets, manual outreach).",
     "bench":"Win count out of 10 criteria: <5 weak • 5–7 fair • 8+ strong"},
    {"key":"ad_split","name":"Ad split test","cost":3,"speed":"days",
     "gain":{"desirability":0.5,"feasibility":0.0,"viability":0.2},
     "desc":"Test two messages to see which resonates with the same audience.",
     "bench":"CTR gap yardsticks: <0.5pp weak • 0.5–1.5pp fair • >1.5pp strong"},
    {"key":"diary_study","name":"Diary study / usage log","cost":2,"speed":"weeks",
     "gain":{"desirability":0.3,"feasibility":0.3,"viability":0.1},
     "desc":"Have target users log pain occurrences for 1–2 weeks.",
     "bench":"Frequent, repeated pain across entries is a strong signal"}
]

# -------------------------- Helpers --------------------------
def push_tab(idx: int):
    # Clicks the tab button (0-based) twice for reliability
    components.html(
        f"<script>const t=window.parent.document.querySelectorAll('button[role=tab]');"
        f"if(t[{idx}]){{t[{idx}].click(); setTimeout(()=>t[{idx}].click(),90);}}</script>", height=0
    )

def init_state():
    st.session_state.s2 = {
        "stage": "intro",                 # intro -> slots -> round1 -> results1 -> round2 -> results2 -> (round3?) -> score
        "tokens": 8,                      # total per round (round1=8, round2=6, round3=4)
        "round": 1,
        "idea": deepcopy(SEED_IDEA),
        "assumptions": [],                # list[{text, bucket, quality}]
        "assumption_slots": 8,
        "portfolio": {1:[],2:[],3:[]},    # chosen experiments per round: list[{exp_key, assumption_idx}]
        "results": {1:[],2:[],3:[]},      # results per round
        "learned_risk": {"desirability":0.0,"feasibility":0.0,"viability":0.0},
        "score": None
    }

def bucket_color(b):
    return {"desirability":"🧡", "feasibility":"💙", "viability":"💚"}[b]

def assumption_quality(text):
    """Simple proxy for specificity: looks for measurable cues and length."""
    t = (text or "").lower()
    cues = sum(x in t for x in [
        "%","$"," per "," click "," signup"," week"," month"," waitlist"," pay"," again"," cohort"," threshold"
    ])
    length = len(t.split())
    return max(0.2, min(1.0, 0.2 + 0.1*cues + 0.02*min(length, 30)))

def experiment_by_key(k):
    return next(e for e in EXPERIMENTS if e["key"]==k)

def interp_band(val, bands):
    """Return a text verdict from (val,bands) like [(2,'weak'),(5,'fair'),...] thresholds in absolute units."""
    for thr, label in bands:
        if val < thr: return label
    return bands[-1][1]

def synth_result(exp, bucket, a_quality):
    """Generate a semi-random snippet biased by ground truth & assumption quality; add interpretation."""
    steer = 1.15 if GROUND_TRUTH["top"][bucket] in ("real_problem","data_access","scalability") else 1.0
    base = exp["gain"].get(bucket, 0.0)
    signal = base * a_quality * steer

    # Variant texts for the ad split to make it actionable
    headline_A = "Keep your mid-week classes full with timely fills"
    headline_B = "Reduce empty spots and stabilize revenue each week"

    if exp["key"]=="landing_page":
        imps = random.randint(320, 900)
        ctr = max(0.5, min(14.0, 2.0 + 12.0*signal + random.uniform(-1.5,1.5)))  # %
        verdict = "weak" if ctr<2 else ("fair" if ctr<5 else ("promising" if ctr<8 else "strong"))
        snippet = (f"Landing page: {imps} impressions → CTR **{ctr:.1f}%** "
                   f"(waitlist signups ≈ **{int(imps*ctr/100*0.6)}**). "
                   f"**Interpretation:** {verdict}. {exp['bench']}")
        return snippet, signal

    if exp["key"]=="ad_split":
        a = max(0.4, min(10.0, 1.3 + 9.0*signal + random.uniform(-1.0,1.0)))
        b = max(0.3, min(9.0, 0.9 + 8.0*(signal-0.08) + random.uniform(-1.0,1.0)))
        diff = abs(a-b)
        winner = "A" if a>b else "B"
        msgA = f"Headline A: “{headline_A}” → CTR **{a:.1f}%**"
        msgB = f"Headline B: “{headline_B}” → CTR **{b:.1f}%**"
        verdict = "weak" if diff<0.5 else ("fair" if diff<1.5 else "strong")
        snippet = (f"Ad split test:\n- {msgA}\n- {msgB}\n"
                   f"Winner: **{winner}** (gap {diff:.1f}pp). "
                   f"**Interpretation:** {verdict}. {exp['bench']}")
        return snippet, signal

    if exp["key"]=="preorder":
        leads = random.randint(10, 30)
        conv = max(0.0, min(0.35, 0.06 + 0.4*signal + random.uniform(-0.05,0.05)))
        buys = max(0, int(leads*conv))
        verdict = "weak" if conv<0.05 else ("fair" if conv<0.12 else "strong")
        snippet = (f"Pre-order: {leads} leads → **{buys}** confirmed cards "
                   f"({conv*100:.1f}% buy). **Interpretation:** {verdict}. {exp['bench']}")
        return snippet, signal

    if exp["key"]=="concierge_mvp":
        trials = random.randint(6, 8)
        repurchase = max(0, int(trials*(0.18 + 0.62*signal + random.uniform(-0.1,0.1))))
        verdict = "weak" if repurchase<=1 else ("fair" if repurchase<=3 else "strong")
        snippet = (f"Concierge trial: {trials} customers → **{repurchase}** would pay again. "
                   f"**Interpretation:** {verdict}. {exp['bench']}")
        return snippet, signal

    if exp["key"]=="wizard_of_oz":
        tasks = random.randint(18, 32)
        auto = int(tasks*(0.5 + 0.4*signal + random.uniform(-0.1,0.1)))
        pct = 100*auto/max(tasks,1)
        verdict = "weak" if pct<50 else ("fair" if pct<70 else "strong")
        snippet = (f"Wizard-of-Oz: automated **{auto}/{tasks}** tasks (**{pct:.0f}%**). "
                   f"**Interpretation:** {verdict}. {exp['bench']}")
        return snippet, signal

    if exp["key"]=="expert_interview":
        insights = 2 + int(4*signal + random.uniform(0,2))
        snippet = (f"Expert interview: **{insights}** specific takeaways; "
                   f"flagged risk emphasis → **{GROUND_TRUTH['top']['viability']}**. "
                   f"**Interpretation:** directional; use to refine next tests. {exp['bench']}")
        return snippet, signal*0.6

    if exp["key"]=="benchmark":
        win = max(3, int(10*signal + random.uniform(-1,2)))
        verdict = "weak" if win<5 else ("fair" if win<8 else "strong")
        snippet = (f"Benchmark vs workaround: won **{win}/10** criteria. "
                   f"**Interpretation:** {verdict}. {exp['bench']}")
        return snippet, signal

    if exp["key"]=="diary_study":
        entries = 6 + int(5*signal + random.uniform(0,3))
        snippet = (f"Diary study: **{entries}** entries. Repeated pain noted: "
                   f"“inconsistent mid-week demand”. **Interpretation:** recurring pain is a strong signal.")
        return snippet, signal*0.7

    return "Result pending", signal

def add_learning(signal, bucket):
    st.session_state.s2["learned_risk"][bucket] = min(
        1.0, st.session_state.s2["learned_risk"][bucket] + 0.6*signal
    )

def compute_score():
    S = st.session_state.s2
    q = [a["quality"] for a in S["assumptions"]]
    aq = (sum(q)/len(q)) if q else 0.0

    rp = 0.0
    if S["results"][1]:
        hits = 0
        for b in ["desirability","feasibility","viability"]:
            top = GROUND_TRUTH["top"][b]
            if any(r["assumption"]["bucket"]==b and top in r["assumption"]["text"].lower() for r in S["results"][1]):
                hits += 1
        rp = hits/3.0

    fits = []
    for rnd in [1,2,3]:
        for r in S["results"][rnd]:
            exp = experiment_by_key(r["exp_key"])
            fits.append(exp["gain"].get(r["assumption"]["bucket"],0.0))
    ef = (sum(fits)/len(fits)) if fits else 0.0

    c_rounds = []
    for rnd in [1,2,3]:
        cost = sum(experiment_by_key(x["exp_key"])["cost"] for x in S["portfolio"][rnd])
        if cost>0: c_rounds.append(cost)
    re = 1.0
    if c_rounds:
        re -= 0.15*max(0, (c_rounds[0]-6)/3)  # penalize heavy spend in round 1
        if len(c_rounds)>=2 and c_rounds[1]==0:
            re -= 0.2                      # no iteration
    re = max(0.0, min(1.0, re))

    lo = sum(1 for b in ["desirability","feasibility","viability"] if S["learned_risk"][b]>0.55) / 3.0

    total = round(100*(0.30*aq + 0.25*rp + 0.25*ef + 0.10*re + 0.10*lo))
    comps = {
        "Assumption Quality": round(aq,2),
        "Risk Prioritization": round(rp,2),
        "Experiment Fit": round(ef,2),
        "Resource Efficiency": round(re,2),
        "Learning Outcome": round(lo,2)
    }
    S["score"] = {"total": total, "components": comps}

# -------------------------- UI helpers --------------------------
def header():
    st.title(TITLE)
    st.caption("Objective: Surface hidden assumptions, prioritize risk, and design scrappy experiments that maximize learning per unit of effort.")

def show_assumption_table():
    S = st.session_state.s2
    if not S["assumptions"]: return
    st.markdown("#### Your assumptions")
    for i,a in enumerate(S["assumptions"]):
        st.write(f"{i+1}. {bucket_color(a['bucket'])} **{a['bucket'].title()}** — {a['text']}  (quality {a['quality']:.2f})")

def assumption_slotting():
    S = st.session_state.s2
    st.subheader("Assumption Slots and Buckets")
    st.info(f"Seed idea: **{S['idea']['name']}** — {S['idea']['sketch']}")

    with st.expander("How to bucket assumptions (with examples)", expanded=True):
        st.markdown("""
- **Desirability** → Demand & willingness to pay.  
  _Example:_ “≥15% of target visitors will join a $10/mo waitlist within 7 days.”
- **Feasibility** → Can we actually deliver the outcome?  
  _Example:_ “We can fill ≥70% of empty spots using the current data sources.”
- **Viability** → The business works (margins, churn, scale).  
  _Example:_ “Gross margin ≥60% at $99/mo with <4 hours/week of ops.”

**Nudge meanings**  
- “**Be more specific**” → add who/what/how much/by when.  
- “**Too broad**” → change “People want it” to a measurable behavior (click, buy, repurchase).  
- “**Looks testable**” → it’s specific enough to run a scrappy experiment.
""")

    cols = st.columns(3)
    bucket = cols[0].selectbox("Bucket", ["desirability","feasibility","viability"], format_func=str.title, key="ass_bucket")
    text = cols[1].text_input("Assumption (specific & testable)", key="ass_text",
                              placeholder="e.g., ≥15% of target visitors will join a $10/mo waitlist within 7 days.")

    nudges = ""
    if text and len(text.split()) < 6:
        nudges = "Be more specific (who, what, how much, by when)."
    if text and any(x in text.lower() for x in ["customers want it","people want it","everyone","they will like it"]):
        nudges = "Too broad. Try a measurable behavior or threshold."

    cols[2].markdown(f"**Nudge:** {nudges or 'Looks testable.'}")
    if cols[2].button("Add assumption", key="btn_add_assumption"):
        if text.strip():
            S["assumptions"].append({"text":text.strip(), "bucket":bucket, "quality":assumption_quality(text)})
            st.rerun()

    show_assumption_table()
    if len(S["assumptions"])<6:
        st.warning("Add at least 6 assumptions to proceed.")
    else:
        if st.button("Proceed to Round 1 experiments", key="btn_to_round1"):
            S["stage"]="round1"
            S["tokens"]=8
            push_tab(2)  # Round 1 tab index
            st.rerun()

def experiment_picker(round_idx):
    S = st.session_state.s2
    st.subheader(f"Round {round_idx}: Pick a portfolio of experiments")
    st.caption("Tip: start with low-cost, high-learning tests. You have **tokens** as a constraint.")
    st.write(f"Tokens available: **{S['tokens']}**")

    a_opts = [f"{i+1}. {a['bucket'].title()} — {a['text'][:60]}" for i,a in enumerate(S["assumptions"])]
    cols = st.columns(2)
    a_idx = cols[0].selectbox("Choose an assumption", list(range(len(S["assumptions"]))),
                              format_func=lambda i: a_opts[i], key=f"a_{round_idx}")
    exp = cols[1].selectbox("Choose an experiment", EXPERIMENTS,
                            format_func=lambda e: f"{e['name']} (cost {e['cost']})", key=f"e_{round_idx}")

    st.caption(f"About this experiment: {exp['desc']}  \n**Benchmarks:** {exp['bench']}")

    if st.button("Add to portfolio", key=f"add_{round_idx}"):
        cost = exp["cost"]
        if cost>S["tokens"]:
            st.error("Not enough tokens for that experiment.")
        else:
            S["tokens"] -= cost
            S["portfolio"][round_idx].append({"assumption_idx": a_idx, "exp_key": exp["key"]})
            st.rerun()

    if S["portfolio"][round_idx]:
        st.markdown("#### Selected this round")
        for n,item in enumerate(S["portfolio"][round_idx], start=1):
            a = S["assumptions"][item["assumption_idx"]]
            e = experiment_by_key(item["exp_key"])
            st.write(f"{n}. {bucket_color(a['bucket'])} **{a['bucket'].title()}** — {a['text']}  →  **{e['name']}** (cost {e['cost']})")

    cols2 = st.columns(2)
    if cols2[0].button("Run experiments", disabled=(len(S["portfolio"][round_idx])==0), key=f"run_{round_idx}"):
        S["results"][round_idx] = []
        for item in S["portfolio"][round_idx]:
            a = S["assumptions"][item["assumption_idx"]]
            e = experiment_by_key(item["exp_key"])
            snippet, signal = synth_result(e, a["bucket"], a["quality"])
            S["results"][round_idx].append({"assumption":a, "exp_key":e["key"], "name":e["name"], "snippet":snippet, "signal":signal})
            add_learning(signal, a["bucket"])
        S["stage"] = f"results{round_idx}"
        push_tab( round_idx + 2 )  # Results tab index: Round1->Results1(3), Round2->Results2(5), Round3->Score handled later
        st.rerun()

def show_results(round_idx, next_tokens=6, next_stage="round2"):
    S = st.session_state.s2
    st.subheader(f"Round {round_idx} results")
    for r in S["results"][round_idx]:
        st.success(f"**{r['name']}** → {r['snippet']}  \n({r['assumption']['bucket'].title()} | assumption quality {r['assumption']['quality']:.2f})")

    st.markdown("#### Risk coverage so far")
    rc = S["learned_risk"]
    st.write(f"- Desirability: {rc['desirability']:.2f}   •   Feasibility: {rc['feasibility']:.2f}   •   Viability: {rc['viability']:.2f}")

    cols = st.columns(2)
    if round_idx<3:
        if cols[0].button("Plan next round", key=f"plan_next_{round_idx}"):
            S["stage"]=next_stage
            S["round"]=round_idx+1
            S["tokens"]=next_tokens
            push_tab( round_idx + 2 )  # Move from ResultsN to Round(N+1) tab
            st.rerun()
    if cols[1].button("Skip to scoring", key=f"skip_to_scoring_{round_idx}"):
        S["stage"]="score"
        compute_score()
        push_tab(7)  # Score tab
        st.rerun()

def score_page():
    S = st.session_state.s2
    if S["score"] is None:
        compute_score()
    st.subheader("Score and Feedback")
    st.metric("Total Score", f"{S['score']['total']}/100")
    st.markdown("#### Category scores")
    for k,v in S["score"]["components"].items():
        label = ("Excellent" if v>=0.8 else "Good" if v>=0.6 else "Needs work")
        st.write(f"- **{k}:** {int(v*100)}/100 — {label}")

    st.markdown("#### Coaching notes")
    st.write("- **Assumption Quality:** Specific, measurable phrasing makes results decisive.")
    st.write("- **Risk Prioritization:** Tackle bucket top risks first; defer nice-to-know items.")
    st.write("- **Experiment Fit:** Pick tests that maximize learning **for that bucket**.")
    st.write("- **Resource Efficiency:** Start scrappy; leave tokens for iteration.")
    st.write("- **Learning Outcome:** End with a clear validated/invalidated statement and next step.")

    if st.button("Restart simulation", key="restart"):
        init_state(); push_tab(0); st.rerun()

# -------------------------- App flow --------------------------
if "s2" not in st.session_state:
    init_state()

S = st.session_state.s2
header()

# Tab order indices: 0 Intro • 1 Assumptions • 2 Round1 • 3 Results1 • 4 Round2 • 5 Results2 • 6 Round3 • 7 Score
tabs = st.tabs(["Intro","Assumptions","Round 1","Results 1","Round 2","Results 2","Round 3 (optional)","Score"])

with tabs[0]:
    st.subheader("What you’ll do in this simulation")
    st.markdown("""
**First you will** write down your key assumptions and sort each one into a risk bucket:
- **Desirability** (Do customers want it? Will they pay?)
- **Feasibility** (Can you deliver it reliably?)
- **Viability** (Does the model work as a business?)

**Then you will** choose quick, scrappy experiments from a menu (e.g., landing page, concierge MVP, pre-order).  
Each experiment has a **token cost**, **speed**, and expected **learning gain** for a bucket.

**Next you will** run a small portfolio of experiments in **Round 1**.  
Results will surface data snippets (CTR, pre-orders, repurchase). Your assumption wording affects how clear the signals are.

**After that you will** decide what to do in **Round 2** (and optional **Round 3**):
- **Pivot** to riskier assumptions, **double-down** on promise, or **tackle** the next critical risk.

**Finally you will** see a score and coaching notes based on:
- **Assumption Quality**, **Risk Prioritization**, **Experiment Fit**, **Resource Efficiency**, **Learning Outcome**.
""")
    if st.button("Start", key="start_intro"):
        S["stage"] = "slots"
        push_tab(1)  # Assumptions tab
        st.rerun()

with tabs[1]:
    if S["stage"] in ["slots","round1","results1","round2","results2","round3","score"]:
        assumption_slotting()

with tabs[2]:
    if S["stage"] in ["round1","results1","round2","results2","round3","score"]:
        experiment_picker(1)

with tabs[3]:
    if S["stage"] in ["results1","round2","results2","round3","score"]:
        show_results(1, next_tokens=6, next_stage="round2")

with tabs[4]:
    if S["stage"] in ["round2","results2","round3","score"]:
        experiment_picker(2)

with tabs[5]:
    if S["stage"] in ["results2","round3","score"]:
        show_results(2, next_tokens=4, next_stage="round3")

with tabs[6]:
    if S["stage"] in ["round3","score"]:
        experiment_picker(3)

with tabs[7]:
    if S["stage"]=="score":
        score_page()
