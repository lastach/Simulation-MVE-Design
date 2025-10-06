# Startup Simulation #2 — Assumptions → Experiments → Learning (Streamlit)
# -----------------------------------------------------------------------
# Run locally:  streamlit run app_sim2.py
# On Streamlit Cloud: deploy with main file path = app_sim2.py
# -----------------------------------------------------------------------

import random
import streamlit as st
from copy import deepcopy

random.seed(17)

st.set_page_config(page_title="Simulation #2: Assumptions → Experiments", page_icon="🧪", layout="wide")
TITLE = "Startup Simulation #2 — Assumptions → Experiments → Learning"

# -------------------------- Seed idea & ground truth (hidden) --------------------------
SEED_IDEA = {
    "name": "GymOps Pilot",
    "sketch": (
        "Lightweight ‘concierge’ service that stabilizes class occupancy for independent gyms. "
        "We watch demand signals and ping owners with fill tactics (swap, incentive, partner push). "
        "Subscription concept, $79–$149/mo."
    )
}

# Hidden “truth” map (guides noisy outcomes). Each bucket gets a top risk.
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
     "desc":"Drive traffic; measure clicks, signups, or waitlist."},
    {"key":"concierge_mvp","name":"Concierge MVP","cost":3,"speed":"days",
     "gain":{"desirability":0.4,"feasibility":0.5,"viability":0.2},
     "desc":"Manually deliver service for a few customers."},
    {"key":"wizard_of_oz","name":"Wizard-of-Oz prototype","cost":3,"speed":"days",
     "gain":{"desirability":0.2,"feasibility":0.6,"viability":0.1},
     "desc":"UI looks real; ops behind the curtain."},
    {"key":"preorder","name":"Pre-order / crowdfunding","cost":4,"speed":"weeks",
     "gain":{"desirability":0.8,"feasibility":0.0,"viability":0.3},
     "desc":"Real buying intent; small set of early adopters."},
    {"key":"expert_interview","name":"Expert interview","cost":1,"speed":"days",
     "gain":{"desirability":0.2,"feasibility":0.2,"viability":0.2},
     "desc":"Talk to seasoned operators; quick signal."},
    {"key":"benchmark","name":"Benchmark vs. workaround","cost":2,"speed":"days",
     "gain":{"desirability":0.3,"feasibility":0.2,"viability":0.3},
     "desc":"Compare behavior vs. current hacks."},
    {"key":"ad_split","name":"Ad split test","cost":3,"speed":"days",
     "gain":{"desirability":0.5,"feasibility":0.0,"viability":0.2},
     "desc":"Message-market fit; CTR vs. variant."},
    {"key":"diary_study","name":"Diary study / usage log","cost":2,"speed":"weeks",
     "gain":{"desirability":0.3,"feasibility":0.3,"viability":0.1},
     "desc":"A week of real behavior + pain notes."},
]

# -------------------------- Helpers --------------------------
def init_state():
    st.session_state.s2 = {
        "stage": "intro",                 # intro -> slots -> round1 -> results1 -> round2 -> results2 -> (round3?) -> score
        "tokens": 8,                      # total per round (round1=8, round2=6, round3=4)
        "round": 1,
        "idea": deepcopy(SEED_IDEA),
        "assumptions": [],                # list of dicts {text, bucket, quality (0..1)}
        "assumption_slots": 8,
        "portfolio": {1:[],2:[],3:[]},    # chosen experiments per round: list of {exp_key, assumption_idx}
        "results": {1:[],2:[],3:[]},      # results per round
        "learned_risk": {"desirability":0.0,"feasibility":0.0,"viability":0.0},  # cumulative coverage signal
        "score": None
    }

def bucket_color(b):
    return {"desirability":"🧡", "feasibility":"💙", "viability":"💚"}[b]

def assumption_quality(text):
    # quick proxy: includes quant or concrete “who/when/how much” cues
    t = (text or "").lower()
    cues = sum(x in t for x in ["%","$"," per "," click "," signup"," week"," month"," waitlist"," pay"," again"," cohort"])
    length = len(t.split())
    return max(0.2, min(1.0, 0.2 + 0.1*cues + 0.02*min(length, 30)))

def experiment_by_key(k): 
    return next(e for e in EXPERIMENTS if e["key"]==k)

def synth_result(exp, bucket, a_quality):
    """Generate a semi-random snippet biased by ground truth & assumption quality."""
    base = exp["gain"].get(bucket, 0.0)
    steer = 1.15 if GROUND_TRUTH["top"][bucket] in ("real_problem","data_access","scalability") else 1.0
    signal = base * a_quality * steer

    if exp["key"]=="landing_page":
        imps = random.randint(300, 800)
        ctr = max(0.5, min(14.0, 2 + 12*signal + random.uniform(-1.5,1.5)))  # %
        return f"Landing page: {imps} impressions → CTR {ctr:.1f}% (waitlist signups ~{int(imps*ctr/100*0.6)})", signal
    if exp["key"]=="ad_split":
        a = max(0.4, min(10.0, 1.2 + 9.0*signal + random.uniform(-1.0,1.0)))
        b = max(0.3, min(9.0, 0.9 + 8.0*(signal-0.1) + random.uniform(-1.0,1.0)))
        winner = "A" if a>b else "B"
        return f"Ad split: CTR A {a:.1f}% vs B {b:.1f}% → Winner {winner}", signal
    if exp["key"]=="preorder":
        leads = random.randint(8, 25)
        conv = max(0.0, min(0.35, 0.05 + 0.4*signal + random.uniform(-0.05,0.05)))
        buys = max(0, int(leads*conv))
        return f"Pre-order: {leads} leads → {buys} confirmed cards ({conv*100:.1f}% buy)", signal
    if exp["key"]=="concierge_mvp":
        trials = random.randint(4, 8)
        repurchase = max(0, int(trials*(0.15 + 0.6*signal + random.uniform(-0.1,0.1))))
        return f"Concierge trial: {trials} customers → {repurchase} would pay again", signal
    if exp["key"]=="wizard_of_oz":
        tasks = random.randint(15, 30)
        success = int(tasks*(0.5 + 0.4*signal + random.uniform(-0.1,0.1)))
        return f"Wizard-of-Oz: {success}/{tasks} tasks completed without human intervention", signal
    if exp["key"]=="expert_interview":
        insights = 2 + int(4*signal + random.uniform(0,2))
        return f"Expert interview: {insights} actionable insights; strongest concern → {GROUND_TRUTH['top']['viability']}", signal*0.6
    if exp["key"]=="benchmark":
        gap = max(3, int(10*signal + random.uniform(-1,2)))
        return f"Benchmark: proposed beats workaround on {gap}/10 criteria", signal
    if exp["key"]=="diary_study":
        entries = 5 + int(5*signal + random.uniform(0,3))
        pain = "inconsistent mid-week demand"
        return f"Diary: {entries} entries; recurring pain = {pain}", signal*0.7
    return "Result pending", signal

def add_learning(signal, bucket):
    st.session_state.s2["learned_risk"][bucket] = min(
        1.0, st.session_state.s2["learned_risk"][bucket] + 0.6*signal
    )

def compute_score():
    S = st.session_state.s2
    # Assumption Quality
    q = [a["quality"] for a in S["assumptions"]]
    aq = (sum(q)/len(q)) if q else 0.0
    # Risk Prioritization: credit if round-1 targeted bucket top risks
    rp = 0.0
    if S["results"][1]:
        hits = 0
        for b in ["desirability","feasibility","viability"]:
            top = GROUND_TRUTH["top"][b]
            if any(r["assumption"]["bucket"]==b and top in r["assumption"]["text"].lower() for r in S["results"][1]):
                hits += 1
        rp = hits/3.0
    # Experiment Fit: bucket-gain alignment
    fits = []
    for rnd in [1,2,3]:
        for r in S["results"][rnd]:
            exp = experiment_by_key(r["exp_key"])
            fits.append(exp["gain"].get(r["assumption"]["bucket"],0.0))
    ef = (sum(fits)/len(fits)) if fits else 0.0
    # Resource Efficiency
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
    # Learning Outcome: clear validate/invalid per bucket?
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
    st.caption("Objective: Surface hidden assumptions, prioritize by risk, and design scrappy experiments that maximize learning per unit of effort.")

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
    st.write("Add **6–8** assumptions. Sort each into: **Desirability**, **Feasibility**, or **Viability**.")
    cols = st.columns(3)
    bucket = cols[0].selectbox("Bucket", ["desirability","feasibility","viability"], format_func=str.title, key="ass_bucket")
    text = cols[1].text_input("Assumption (specific & testable)", key="ass_text", placeholder="e.g., 20% of target will join a $10/mo waitlist within one week")
    nudges=""
    if text and len(text.split())<6:
        nudges="Be more specific (who, what, how much, by when)."
    if text and any(x in text.lower() for x in ["customers want it","people want it","everyone"]):
        nudges="Too broad. Try: measurable behavior or threshold."
    cols[2].markdown(f"**Nudge:** {nudges or 'Looks testable.'}")
    if cols[2].button("Add assumption"):
        if text.strip():
            S["assumptions"].append({"text":text.strip(), "bucket":bucket, "quality":assumption_quality(text)})
            st.rerun()

    show_assumption_table()
    if len(S["assumptions"])<6:
        st.warning("Add at least 6 assumptions to proceed.")
    else:
        if st.button("Proceed to Round 1 experiments"):
            S["stage"]="round1"
            S["tokens"]=8
            st.rerun()

def experiment_picker(round_idx):
    S = st.session_state.s2
    st.subheader(f"Round {round_idx}: Pick a portfolio of experiments")
    st.caption("Tip: start with low-cost, high-learning tests. You have **tokens** as a constraint.")
    st.write(f"Tokens available: **{S['tokens']}**")
    # chooser
    a_opts = [f"{i+1}. {a['bucket'].title()} — {a['text'][:60]}" for i,a in enumerate(S["assumptions"])]
    cols = st.columns(2)
    a_idx = cols[0].selectbox("Choose an assumption", list(range(len(S["assumptions"]))), format_func=lambda i: a_opts[i], key=f"a_{round_idx}")
    exp = cols[1].selectbox("Choose an experiment", EXPERIMENTS, format_func=lambda e: f"{e['name']} (cost {e['cost']})", key=f"e_{round_idx}")
    if st.button("Add to portfolio", key=f"add_{round_idx}"):
        cost = exp["cost"]
        if cost>S["tokens"]:
            st.error("Not enough tokens for that experiment.")
        else:
            S["tokens"] -= cost
            S["portfolio"][round_idx].append({"assumption_idx": a_idx, "exp_key": exp["key"]})
            st.rerun()

    # show portfolio
    if S["portfolio"][round_idx]:
        st.markdown("#### Selected this round")
        for item in S["portfolio"][round_idx]:
            a = S["assumptions"][item["assumption_idx"]]
            e = experiment_by_key(item["exp_key"])
            st.write(f"- {bucket_color(a['bucket'])} **{a['bucket'].title()}** — {a['text']}  →  **{e['name']}** (cost {e['cost']})")

    cols2 = st.columns(2)
    if cols2[0].button("Run experiments", disabled=(len(S["portfolio"][round_idx])==0), key=f"run_{round_idx}"):
        # generate results
        S["results"][round_idx] = []
        for item in S["portfolio"][round_idx]:
            a = S["assumptions"][item["assumption_idx"]]
            e = experiment_by_key(item["exp_key"])
            snippet, signal = synth_result(e, a["bucket"], a["quality"])
            S["results"][round_idx].append({"assumption":a, "exp_key":e["key"], "name":e["name"], "snippet":snippet, "signal":signal})
            add_learning(signal, a["bucket"])
        S["stage"] = f"results{round_idx}"
        st.rerun()

def show_results(round_idx, next_tokens=6, next_stage="round2"):
    S = st.session_state.s2
    st.subheader(f"Round {round_idx} results")
    for r in S["results"][round_idx]:
        st.success(f"**{r['name']}** → {r['snippet']}  \n({r['assumption']['bucket'].title()} | assumption quality {r['assumption']['quality']:.2f})")
    # simple coverage view
    st.markdown("#### Risk coverage so far")
    rc = S["learned_risk"]
    st.write(f"- Desirability: {rc['desirability']:.2f}   •   Feasibility: {rc['feasibility']:.2f}   •   Viability: {rc['viability']:.2f}")

    cols = st.columns(2)
    if round_idx<3:
        if cols[0].button("Plan next round"):
            S["stage"]=next_stage
            S["round"]=round_idx+1
            S["tokens"]=next_tokens
            st.rerun()
    if cols[1].button("Skip to scoring"):
        S["stage"]="score"
        compute_score()
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

    if st.button("Restart simulation"):
        init_state(); st.rerun()

# -------------------------- App flow --------------------------
if "s2" not in st.session_state:
    init_state()

S = st.session_state.s2
header()

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
Results will surface data snippets (e.g., CTR, pre-orders). Your assumption wording affects how clear the signals are.

**After that you will** decide what to do in **Round 2** (and optional **Round 3**):
- **Pivot** to riskier assumptions,
- **Double-down** on something promising, or
- **Tackle** the next critical risk.

**Finally you will** see a score and coaching notes based on:
- **Assumption Quality** (specific & measurable),
- **Risk Prioritization** (did you test the riskiest things first?),
- **Experiment Fit** (right test for the right risk),
- **Resource Efficiency** (smart token use), and
- **Learning Outcome** (clear validate/invalidate + next step).
""")
    if st.button("Start"):
        S["stage"] = "slots"
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
