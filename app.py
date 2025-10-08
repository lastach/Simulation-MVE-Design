# app_sim2.py
# Simulation #2 — Designing & Running Early Experiments (ThermaLoop)
# Requires: streamlit, pandas, streamlit-dnd-list
# Run: streamlit run app_sim2.py

import random
from typing import Dict, Any, List, Tuple
import pandas as pd
import streamlit as st

# Drag & drop component
try:
    from streamlit_dnd_list import dnd_list
except Exception:
    dnd_list = None

# --- TEMP: force fallback so the app never crashes if the lib isn't present ---
FORCE_NO_DND = True
if FORCE_NO_DND:
    dnd_list = None
# ------------------------------------------------------------------------------

st.set_page_config(page_title="Simulation #2 — Scrappy Experiments", page_icon="🧪", layout="wide")
random.seed(42)

TITLE = "Simulation #2 — Designing & Running Early Experiments"
SUB   = "ThermaLoop: rank risks, pick scrappy tests, learn quickly"

# ───────────────────────────────────────────────────────────────────────────────
# IDEA CARDS — each assumption includes tags, hidden truth, and a risk type:
# risk: 'D' (Desirability), 'F' (Feasibility), 'V' (Viability)
# ───────────────────────────────────────────────────────────────────────────────

IDEA_CARDS: Dict[str, Dict[str, Any]] = {
    "Comfort-First Home Kit (Homeowners)": {
        "desc": "Smart vent retrofit for homeowners to fix hot/cold rooms quickly and affordably.",
        "assumptions": [
            {"id":"A1","text":"Uneven room temperature is a top-3 annoyance for target homeowners.","tags":["demand","comfort"],"truth":"M","risk":"D"},
            {"id":"A2","text":"Homeowners will pay $200–$300 for noticeable comfort improvement even without energy savings.","tags":["wtp","pricing","comfort"],"truth":"M","risk":"D"},
            {"id":"A3","text":"Install can be completed in under 20 minutes by a non-expert.","tags":["install_time","feasibility"],"truth":"H","risk":"F"},
            {"id":"A4","text":"The device fits 90% of standard vent sizes without modification.","tags":["compat","feasibility"],"truth":"M","risk":"F"},
            {"id":"A5","text":"Comfort improvement is noticeable within 48 hours.","tags":["comfort","time_to_value"],"truth":"L","risk":"D"},
            {"id":"A6","text":"Noise from the motor is no louder than a typical fan at night.","tags":["noise","quality"],"truth":"M","risk":"F"},
            {"id":"A7","text":"Self-install is preferred over calling a contractor.","tags":["channel","self_install","demand"],"truth":"L","risk":"D"},
            {"id":"A8","text":"App setup can be completed in under 5 minutes.","tags":["onboarding","feasibility","ux"],"truth":"M","risk":"F"},
            {"id":"A9","text":"Customers prefer comfort gains over energy savings as the main benefit.","tags":["positioning","comfort"],"truth":"L","risk":"D"},
            {"id":"A10","text":"Users will share/advocate if it fixes a daily annoyance.","tags":["referral","demand"],"truth":"M","risk":"V"},
        ],
    },
    "Installer-Enablement System (HVAC channel)": {
        "desc": "Toolkit sold via installers to reduce callbacks and create an upsell.",
        "assumptions": [
            {"id":"B1","text":"Installers experience at least 2+ comfort-related callbacks per month.","tags":["callbacks","installer_econ"],"truth":"L","risk":"V"},
            {"id":"B2","text":"Reducing callbacks measurably improves NPS/reviews for installers.","tags":["callbacks","evidence"],"truth":"M","risk":"V"},
            {"id":"B3","text":"A 15–20% commission is enough incentive to promote the product.","tags":["commission","wtp_installer"],"truth":"M","risk":"V"},
            {"id":"B4","text":"Installers can learn install steps within 30 minutes after training.","tags":["training","feasibility"],"truth":"H","risk":"F"},
            {"id":"B5","text":"The kit adds ≤15 minutes to a typical job.","tags":["install_time","feasibility"],"truth":"M","risk":"F"},
            {"id":"B6","text":"Homeowners trust installer upsells for comfort solutions.","tags":["trust","channel"],"truth":"M","risk":"D"},
            {"id":"B7","text":"A manufacturer-backed guarantee is sufficient to reduce installer risk.","tags":["warranty","risk"],"truth":"M","risk":"V"},
            {"id":"B8","text":"Avoiding one callback per month makes the product worthwhile.","tags":["unit_econ","roi_installer"],"truth":"M","risk":"V"},
            {"id":"B9","text":"Utility rebates significantly improve close rates.","tags":["rebates","viability"],"truth":"L","risk":"V"},
            {"id":"B10","text":"Installers will use a companion training/certification app.","tags":["training","adoption"],"truth":"M","risk":"D"},
        ],
    },
    "Landlord Energy Optimization Service (Property owners)": {
        "desc": "Managed subscription for landlords to reduce HVAC waste and complaints across units.",
        "assumptions": [
            {"id":"C1","text":"Landlords track heating/cooling complaints as a meaningful KPI.","tags":["complaints","ops"],"truth":"M","risk":"D"},
            {"id":"C2","text":"Payback under 24 months is essential for adoption.","tags":["payback","viability"],"truth":"H","risk":"V"},
            {"id":"C3","text":"Monthly subscription pricing is preferred over upfront purchases.","tags":["pricing_model","subscription"],"truth":"M","risk":"V"},
            {"id":"C4","text":"Tenants will not tamper with installed devices.","tags":["tamper","reliability"],"truth":"M","risk":"F"},
            {"id":"C5","text":"Bulk installs (≥10 units/day) are feasible with small teams.","tags":["deployment","feasibility"],"truth":"H","risk":"F"},
            {"id":"C6","text":"Property managers can act on real-time temperature alerts.","tags":["ops","alerting","activation"],"truth":"M","risk":"F"},
            {"id":"C7","text":"Utility rebates significantly improve ROI and adoption.","tags":["rebates","viability"],"truth":"L","risk":"V"},
            {"id":"C8","text":"Reduced tenant turnover is more valued than direct energy savings.","tags":["value","positioning"],"truth":"M","risk":"D"},
            {"id":"C9","text":"Maintenance teams can handle retrofits without third parties.","tags":["maintenance","feasibility"],"truth":"M","risk":"F"},
            {"id":"C10","text":"'Smart sustainability features' improve property marketing.","tags":["marketing","demand"],"truth":"L","risk":"D"},
        ],
    },
}

# Experiments: description + example + cost + tags they fit best
EXPERIMENTS = {
    "Landing Page Test":   {"cost":2, "fits":["demand","wtp","positioning","pricing"], "desc":"Quick page + traffic to measure message/price intent.", "example":"1,200 visits → 58 sign-ups (4.8%)."},
    "Concierge Trial":     {"cost":3, "fits":["comfort","time_to_value","quality","ux"], "desc":"Manually deliver the service to 3–5 targets; observe behavior.", "example":"3 homes → 2 report clear comfort gain; avg Δ 2.1°F."},
    "Prototype Demo":      {"cost":3, "fits":["feasibility","install_time","compat","noise","onboarding"], "desc":"Lightweight mock or video walkthrough; observe usability and install time.", "example":"Install 18 min; jams 1; ~35 dB night noise."},
    "Expert Interview":    {"cost":1, "fits":["training","ops","warranty","rebates","channel","trust"], "desc":"Interview 1–2 experts for constraints and realism.", "example":"Tech: ‘≤20 min install feasible if grille sizes standard.’"},
    "Pre-Order Test":      {"cost":4, "fits":["wtp","pricing","subscription"], "desc":"Collect soft payments or deposits at target price points.", "example":"80 leads → 4 confirmed cards at $249."},
    "Data Comparison":     {"cost":3, "fits":["comfort","evidence","callbacks","unit_econ","payback"], "desc":"Measure comfort/complaints/ROI vs current setup.", "example":"Avg room Δ 2.4°F; complaints down from 3→1."},
    "Ad Split Test":       {"cost":2, "fits":["positioning","demand"], "desc":"Compare comfort-first vs savings-first messaging performance.", "example":"Comfort headline CTR +1.1pp vs savings."},
    "Diary / Usage Log":   {"cost":3, "fits":["comfort","time_to_value"], "desc":"Two-week night-temp and complaint log for baseline vs after.", "example":"Night swings reduced on 5 of 7 nights."},
}

# Round token policy (use as many as you want in R1)
TOKENS = {"r1": 8, "r2": 4, "r3": 4}  # total budget = 16 tokens

# ───────────────────────────────────────────────────────────────────────────────
# Utility
# ───────────────────────────────────────────────────────────────────────────────
def clamp(x, lo, hi): return max(lo, min(hi, x))

def fit_score(exp_name: str, assumption_tags: List[str]) -> float:
    """How well an experiment type matches an assumption's tags."""
    exp = EXPERIMENTS[exp_name]
    overlap = len(set(exp["fits"]).intersection(assumption_tags))
    return min(1.0, 0.35 + 0.22 * overlap)  # base + per overlap

def truth_bias(truth: str) -> float:
    """H: harder to validate (lower success prob), M: mixed, L: easier."""
    return {"H": 0.35, "M": 0.55, "L": 0.75}[truth]

def simulate_result(exp_name: str, assumption: Dict[str,Any]) -> Dict[str,Any]:
    """Generate a data snippet influenced by truth + fit + randomness."""
    base = truth_bias(assumption["truth"])
    fit  = fit_score(exp_name, assumption["tags"])
    p_success = clamp(0.12 + 0.65*fit*base + random.uniform(-0.08, 0.08), 0.05, 0.97)

    if exp_name == "Landing Page Test":
        visits = random.randint(600, 1800)
        ctr = round(100*clamp(random.gauss(0.035 + 0.03*(fit-0.5), 0.01), 0.005, 0.12), 1)  # %
        signup = round(100*clamp(random.gauss(0.03 + 0.025*(fit-0.5), 0.01), 0.003, 0.10), 1)
        verdict = "positive" if random.random() < p_success else "weak"
        note = "Comfort headline outperformed savings by +0.9pp." if fit>0.6 else "Signal present but modest."
        return {"metric": f"{visits} visits • CTR {ctr}% • Signup {signup}%", "verdict": verdict, "note": note}

    if exp_name == "Concierge Trial":
        n = random.randint(3,5)
        noticed = random.randint(max(1,int(n*(0.4+0.4*fit))), n)
        temp_delta = round(random.uniform(1.0, 3.5)*(0.8+0.6*fit), 1)
        verdict = "positive" if random.random() < p_success else "mixed"
        note = f"{noticed}/{n} reported clear comfort gain; avg Δ {temp_delta}°F."
        return {"metric": note, "verdict": verdict, "note":"Manual effort; strong qual."}

    if exp_name == "Prototype Demo":
        jams = max(0, int(random.gauss(1.2 - 1.0*fit, 0.7)))
        install = round(random.uniform(12, 28) * (1.1 - 0.5*fit), 0)
        noise = round(random.uniform(30, 45) * (1.2 - 0.3*fit), 0)  # dB
        verdict = "positive" if (random.random() < p_success and jams<=1 and install<=20) else ("mixed" if jams<=2 else "negative")
        return {"metric": f"Install {install} min • jams {jams} • ~{noise} dB", "verdict": verdict, "note":"Usability & reliability observed."}

    if exp_name == "Expert Interview":
        key = random.choice(["install ≤20 min feasible if sizes standard","training curve moderate","rebate pathway promising","warranty expectation high"])
        verdict = "positive" if random.random() < p_success else "weak"
        return {"metric": f"Expert view: {key}", "verdict": verdict, "note":"Directional feasibility/viability."}

    if exp_name == "Pre-Order Test":
        leads = random.randint(60, 220)
        cards = int(leads * clamp(0.03 + 0.05*(fit-0.5) + random.uniform(-0.01,0.01), 0.01, 0.12))
        verdict = "positive" if random.random() < p_success and cards>=3 else "weak"
        return {"metric": f"{leads} leads • {cards} confirmed cards", "verdict": verdict, "note":"WTP signal w/ price sensitivity."}

    if exp_name == "Data Comparison":
        delta = round(random.uniform(1.0, 3.0)*(0.9+0.5*fit), 1)
        complaints = random.randint(0, max(0, int(3 - 2*fit + random.uniform(-1,1))))
        verdict = "positive" if random.random() < p_success else ("mixed" if complaints<=1 else "weak")
        return {"metric": f"Avg room Δ {delta}°F • complaints {complaints}", "verdict": verdict, "note":"Quant baseline improved."}

    if exp_name == "Ad Split Test":
        ctr_diff = round(100*clamp(random.gauss(0.008*(1+fit), 0.003), 0.002, 0.02), 1)
        verdict = "positive" if random.random() < p_success else "weak"
        return {"metric": f"Comfort headline CTR +{ctr_diff}pp vs savings", "verdict": verdict, "note":"Positioning preference."}

    if exp_name == "Diary / Usage Log":
        improved_nights = random.randint(3,7)
        verdict = "positive" if random.random() < p_success else "mixed"
        return {"metric": f"Improved comfort on {improved_nights}/7 tracked nights", "verdict": verdict, "note":"Temporal pattern captured."}

    return {"metric":"—","verdict":"weak","note":"Noisy read."}

# ───────────────────────────────────────────────────────────────────────────────
# APP STATE
# ───────────────────────────────────────────────────────────────────────────────
def init_state():
    st.session_state.sim2 = {
        "stage":"intro",
        "idea_key": None,
        "ranking_ids": [],  # drag-and-drop result (assumption IDs)
        "r1": {"picked": [], "results": {}, "statuses": {}, "tokens": 0},
        "r2": {"picked": [], "results": {}, "statuses": {}, "tokens": 0},
        "r3": {"picked": [], "results": {}, "statuses": {}, "tokens": 0},
        "assumption_status": {},  # global current status by assumption_id
        "learning": {"most_reduced": None, "evidence": "", "remaining": None, "next_test": None, "success_metric": ""},
        "score": None,
        "reasons": {},
    }
if "sim2" not in st.session_state:
    init_state()
S = st.session_state.sim2

# ───────────────────────────────────────────────────────────────────────────────
# STAGE BAR
# ───────────────────────────────────────────────────────────────────────────────
STAGES = ["intro","idea","rank","r1_select","r1_results","r2_select","r2_results","r3_select","r3_results","summary","score"]
LABELS = {
    "intro":"Intro",
    "idea":"Choose Idea",
    "rank":"Rank Risks",
    "r1_select":"Round 1 — Select",
    "r1_results":"Round 1 — Results",
    "r2_select":"Round 2 — Select",
    "r2_results":"Round 2 — Results",
    "r3_select":"Round 3 — Select",
    "r3_results":"Round 3 — Results",
    "summary":"Learning Summary",
    "score":"Feedback & Score"
}
def stage_bar():
    cols = st.columns(len(STAGES))
    for i,k in enumerate(STAGES):
        cur = STAGES.index(S["stage"])
        prefix = "✅ " if i < cur else ("👉 " if i == cur else "")
        if cols[i].button(f"{prefix}{LABELS[k]}", key=f"nav_{k}"):
            if i <= cur:  # back-only navigation
                S["stage"] = k
                st.rerun()

# ───────────────────────────────────────────────────────────────────────────────
# HELPERS
# ───────────────────────────────────────────────────────────────────────────────
def get_idea() -> Dict[str,Any]:
    return IDEA_CARDS[S["idea_key"]] if S["idea_key"] else None

def tokens_left(round_key:str) -> int:
    cap = TOKENS[round_key]
    return cap - S[round_key]["tokens"]

def add_pick(round_key:str, a_id:str, exp_name:str) -> Tuple[bool,str]:
    cost = EXPERIMENTS[exp_name]["cost"]
    if S[round_key]["tokens"] + cost > TOKENS[round_key]:
        return False, f"Not enough tokens. Cost {cost}, available {tokens_left(round_key)}."
    S[round_key]["picked"].append((a_id, exp_name))
    S[round_key]["tokens"] += cost
    return True, "Added."

def run_round(round_key:str):
    idea = get_idea()
    for a_id, exp_name in S[round_key]["picked"]:
        if a_id not in S[round_key]["results"]:
            a = next(a for a in idea["assumptions"] if a["id"]==a_id)
            S[round_key]["results"][a_id] = simulate_result(exp_name, a)

def assumption_map() -> Dict[str,Dict[str,Any]]:
    return {a["id"]:a for a in get_idea()["assumptions"]}

def risk_label(r:str) -> str:
    return {"D":"Desirability","F":"Feasibility","V":"Viability"}[r]

# ───────────────────────────────────────────────────────────────────────────────
# SCORING
# ───────────────────────────────────────────────────────────────────────────────
def compute_scoring():
    amap = assumption_map()

    # Assumption Clarity: base for pre-written measurable assumptions; bump if they tested >=4 distinct assumptions
    tested_ids = set([a for a,_ in S["r1"]["picked"]+S["r2"]["picked"]+S["r3"]["picked"]])
    clarity = clamp(0.8 + (0.1 if len(tested_ids)>=4 else 0), 0, 1)
    clarity_score = int(100*clarity)

    # Risk Prioritization: sequence in Round 1 should prefer D → F → V
    r1_ids = [a for a,_ in S["r1"]["picked"]]
    seq = [amap[i]["risk"] for i in r1_ids]
    # score pattern: D first items weighted heavier, then F, then V
    weights = {"D":1.0,"F":0.6,"V":0.3}
    if not seq:
        prioritization = 0
    else:
        # average weight, plus bonus if first pick is D and at least one F before V
        avgw = sum(weights[x] for x in seq)/len(seq)
        bonus = 0.1 if (seq and seq[0]=="D") else 0
        if "V" in seq and "F" in seq and seq.index("F") < seq.index("V"):
            bonus += 0.1
        prioritization = clamp(avgw + bonus, 0, 1)
    prioritization_score = int(100*prioritization)

    # Experiment Fit: average fit across all picks
    def avg_fit(picks):
        if not picks: return 0
        vals=[]
        for a_id, exp in picks:
            vals.append(fit_score(exp, amap[a_id]["tags"]))
        return sum(vals)/len(vals)
    fit_avg = clamp(avg_fit(S["r1"]["picked"] + S["r2"]["picked"] + S["r3"]["picked"]), 0, 1)
    fit_score_val = int(100*fit_avg)

    # Resource Efficiency: kept within per-round caps and used ≥3 unique methods
    unique_methods = len(set(exp for _,exp in S["r1"]["picked"]+S["r2"]["picked"]+S["r3"]["picked"]))
    within_caps = 1.0 if (S["r1"]["tokens"]<=TOKENS["r1"] and S["r2"]["tokens"]<=TOKENS["r2"] and S["r3"]["tokens"]<=TOKENS["r3"]) else 0.6
    diversity = clamp((unique_methods/4), 0, 1)  # normalize a bit
    efficiency = clamp(0.6*within_caps + 0.4*diversity, 0, 1)
    efficiency_score = int(100*efficiency)

    # Learning Outcome: statuses consistent with verdicts
    def status_points(rd):
        pts=0; n=0
        for a_id, _ in S[rd]["picked"]:
            res = S[rd]["results"].get(a_id, {})
            stt = S[rd]["statuses"].get(a_id, "")
            if not res or not stt: continue
            n+=1
            if res["verdict"]=="positive" and stt in ["Validated","Weakened"]:
                pts+=1
            elif res["verdict"]=="negative" and stt in ["Invalidated","Still Risky"]:
                pts+=1
            elif res["verdict"]=="mixed" and stt in ["Weakened","Still Risky"]:
                pts+=1
            elif res["verdict"]=="weak" and stt in ["Still Risky"]:
                pts+=1
        return (pts/max(1,n))
    learn = clamp(0.5*status_points("r1")+0.5*status_points("r2"), 0, 1)
    if S["r3"]["picked"]:
        learn = clamp(0.4*status_points("r2")+0.6*status_points("r3"), 0, 1)
    learning_score = int(100*learn)

    total = int(0.30*clarity_score + 0.25*prioritization_score + 0.25*fit_score_val + 0.10*efficiency_score + 0.10*learning_score)
    S["score"] = {
        "total": total,
        "components": {
            "Assumption Clarity": clarity_score,
            "Risk Prioritization": prioritization_score,
            "Experiment Fit": fit_score_val,
            "Resource Efficiency": efficiency_score,
            "Learning Outcome": learning_score
        }
    }

    # Reason strings (specific to choices)
    def list_ids(picks): return ", ".join([f"{i} ({risk_label(amap[i]['risk'])})" for i,_ in picks]) or "none"
    def top_methods(): 
        return ", ".join(sorted(set(exp for _,exp in S["r1"]["picked"]+S["r2"]["picked"]+S["r3"]["picked"]))) or "none"

    reasons = {}
    reasons["Assumption Clarity"] = f"You tested {len(tested_ids)} distinct assumptions: {', '.join(sorted(tested_ids)) or '—'}."
    if r1_ids:
        seq_str = " → ".join(risk_label(x) for x in seq)
        reasons["Risk Prioritization"] = f"Round 1 order: {seq_str}. Recommended emphasis is Desirability → Feasibility → Viability."
    else:
        reasons["Risk Prioritization"] = "No Round 1 picks; score reduced."
    reasons["Experiment Fit"] = f"Chosen methods: {top_methods()}. Average fit to your assumptions’ tags was ~{int(100*fit_avg)}%."
    reasons["Resource Efficiency"] = f"Tokens used (R1/R2/R3): {S['r1']['tokens']}/{S['r2']['tokens']}/{S['r3']['tokens']}. Unique methods: {unique_methods}."
    reasons["Learning Outcome"] = "Statuses generally matched evidence across rounds." if learning_score>=70 else "Several statuses didn’t align with the experiment evidence—recheck positive vs mixed vs weak results."
    S["reasons"] = reasons

# ───────────────────────────────────────────────────────────────────────────────
# UI PAGES
# ───────────────────────────────────────────────────────────────────────────────
def header():
    st.title(TITLE)
    st.caption(SUB)
    stage_bar()
    st.progress((STAGES.index(S["stage"])+1)/len(STAGES))
    st.divider()

def page_intro():
    st.subheader("First you will…")
    st.markdown("""
1) Choose a **direction (Idea Card)**.  
2) **Rank** all assumptions (drag & drop) from highest → lowest risk.  
3) **Round 1:** Use up to **8 tokens** on experiments for your top risks.  
4) Review **results** and set **statuses** (Validated / Weakened / Still Risky / Invalidated).  
5) **Round 2:** Another **4 tokens**.  
6) **Round 3 (optional):** Final **4 tokens** for a big bet.  
7) Complete a short **Learning Summary** → **Score & coaching**.
""")
    if st.button("Start"):
        S["stage"]="idea"; st.rerun()

def page_idea():
    st.subheader("Choose your idea card")
    cols = st.columns(3)
    for i,k in enumerate(IDEA_CARDS.keys()):
        with cols[i]:
            st.markdown(f"**{k}**")
            st.caption(IDEA_CARDS[k]["desc"])
            df = pd.DataFrame([{"Assumption":a["text"], "Risk":risk_label(a["risk"])} for a in IDEA_CARDS[k]["assumptions"]])
            st.dataframe(df, use_container_width=True, hide_index=True, height=min(320, 40*len(df)+30))
            if st.button(f"Work on this", key=f"pick_{k}"):
                S["idea_key"]=k
                S["assumption_status"] = {a["id"]:"Unassessed" for a in IDEA_CARDS[k]["assumptions"]}
                S["ranking_ids"] = [a["id"] for a in IDEA_CARDS[k]["assumptions"]]
                S["stage"]="rank"; st.rerun()

def page_rank():
    st.subheader("Rank your assumptions (highest → lowest risk)")
    if dnd_list is None:
        st.error("Drag & drop requires the package `streamlit-dnd-list`. Add it to requirements.txt and rerun.")
        st.stop()
    amap = assumption_map()
    items = [f"{aid} — {amap[aid]['text']}  \n*{risk_label(amap[aid]['risk'])}*" for aid in S["ranking_ids"]]
    st.caption("Drag items to reorder. Top items will be emphasized in Round 1.")
    reordered = dnd_list(items, direction="vertical", draggable=True)
    # Map back to IDs
    new_ids = [txt.split(" — ")[0] for txt in reordered] if reordered else S["ranking_ids"]
    if new_ids != S["ranking_ids"]:
        S["ranking_ids"] = new_ids
    c1,c2 = st.columns(2)
    if c1.button("Back"):
        S["stage"]="idea"; st.rerun()
    if c2.button("Proceed to Round 1"):
        S["stage"]="r1_select"; st.rerun()

def render_experiment_cards(round_key:str):
    st.markdown(f"**Token budget for this round:** {TOKENS[round_key]} • **Remaining:** {tokens_left(round_key)}")
    amap = assumption_map()
    # Show assumptions in ranked order; for each, allow picking an experiment
    for aid in S["ranking_ids"]:
        a = amap[aid]
        with st.expander(f"{aid} — {a['text']}  |  Risk: {risk_label(a['risk'])}"):
            # Show already-chosen tests for this assumption in this round
            chosen_here = [(i,e) for (i,e) in S[round_key]["picked"] if i==aid]
            if chosen_here:
                st.caption("Chosen for this assumption:")
                for _,e in chosen_here:
                    st.write(f"- {e} (cost {EXPERIMENTS[e]['cost']})")
            # Experiment cards (2 cols grid)
            exps = list(EXPERIMENTS.keys())
            for row in [exps[i:i+2] for i in range(0,len(exps),2)]:
                cols = st.columns(len(row))
                for j, ename in enumerate(row):
                    e = EXPERIMENTS[ename]
                    with cols[j]:
                        with st.container(border=True):
                            st.markdown(f"**{ename}**  \n_{e['desc']}_")
                            st.caption(f"Example: {e['example']}")
                            st.markdown(f"Cost: **{e['cost']}**  •  Fit: ~**{int(100*fit_score(ename, a['tags']))}%**")
                            if st.button(f"Use on {aid}", key=f"use_{round_key}_{aid}_{ename}"):
                                ok,msg = add_pick(round_key, aid, ename)
                                if ok: st.success("Added."); st.rerun()
                                else:  st.warning(msg)

    st.metric("Tokens used", f"{S[round_key]['tokens']}/{TOKENS[round_key]}")

def page_r1_select():
    st.subheader("Round 1 — choose tests for the top risks")
    st.info("Tip: Prioritize **Desirability** first, then **Feasibility**, then **Viability**.")
    render_experiment_cards("r1")
    c1,c2 = st.columns(2)
    if c1.button("Back to ranking"):
        S["stage"]="rank"; st.rerun()
    if c2.button("Run Round 1"):
        if not S["r1"]["picked"]:
            st.warning("Pick at least one experiment before running.")
        else:
            run_round("r1")
            S["stage"]="r1_results"; st.rerun()

def render_results(round_key:str):
    amap = assumption_map()
    for a_id, exp in S[round_key]["picked"]:
        a = amap[a_id]
        res = S[round_key]["results"][a_id]
        with st.container(border=True):
            st.write(f"**{a_id} — {a['text']}**  \n_Experiment: {exp} • cost {EXPERIMENTS[exp]['cost']}_")
            st.write(f"**Data:** {res['metric']}")
            st.caption(res["note"])
            # status selector
            key=f"status_{round_key}_{a_id}"
            default = S[round_key]["statuses"].get(a_id, "Still Risky")
            S[round_key]["statuses"][a_id] = st.selectbox("Set status", ["Validated","Weakened","Still Risky","Invalidated"], index=["Validated","Weakened","Still Risky","Invalidated"].index(default), key=key)
    # propagate to global
    for aid, stt in S[round_key]["statuses"].items():
        S["assumption_status"][aid] = stt

def page_r1_results():
    st.subheader("Round 1 — results & update statuses")
    render_results("r1")
    c1,c2 = st.columns(2)
    if c1.button("Back to Round 1 selection"):
        S["stage"]="r1_select"; st.rerun()
    if c2.button("Proceed to Round 2"):
        S["stage"]="r2_select"; st.rerun()

def page_r2_select():
    st.subheader("Round 2 — choose next tests")
    st.info("Address unresolved risks or pivot to the next-highest items in your ranking.")
    render_experiment_cards("r2")
    c1,c2 = st.columns(2)
    if c1.button("Back to Round 1 results"):
        S["stage"]="r1_results"; st.rerun()
    if c2.button("Run Round 2"):
        if not S["r2"]["picked"]:
            st.warning("Pick at least one experiment before running.")
        else:
            run_round("r2")
            S["stage"]="r2_results"; st.rerun()

def page_r2_results():
    st.subheader("Round 2 — results & update statuses")
    render_results("r2")
    c1,c2,c3 = st.columns(3)
    if c1.button("Proceed to Round 3"):
        S["stage"]="r3_select"; st.rerun()
    if c2.button("Back to Round 2 selection"):
        S["stage"]="r2_select"; st.rerun()
    if c3.button("Skip to Learning Summary"):
        S["stage"]="summary"; st.rerun()

def page_r3_select():
    st.subheader("Round 3 — final big-bet tests")
    st.info("Use the last tokens on one or two high-impact confirmations.")
    render_experiment_cards("r3")
    c1,c2 = st.columns(2)
    if c1.button("Back to Round 2 results"):
        S["stage"]="r2_results"; st.rerun()
    if c2.button("Run Round 3"):
        if not S["r3"]["picked"]:
            st.warning("Pick at least one experiment or go back.")
        else:
            run_round("r3")
            S["stage"]="r3_results"; st.rerun()

def page_r3_results():
    st.subheader("Round 3 — results & update statuses")
    render_results("r3")
    c1,c2 = st.columns(2)
    if c1.button("Back to Round 3 selection"):
        S["stage"]="r3_select"; st.rerun()
    if c2.button("Proceed to Learning Summary"):
        S["stage"]="summary"; st.rerun()

def page_summary():
    st.subheader("Learning summary & next steps")
    amap = assumption_map()
    ids = [a for a in S["assumption_status"].keys()]
    texts = {i:amap[i]["text"] for i in ids}
    c1,c2 = st.columns(2)
    with c1:
        S["learning"]["most_reduced"] = st.selectbox("Top risk you reduced", options=["—"]+ids, format_func=lambda i: ("—" if i=="—" else f"{i}: {texts[i]}"), index=0 if not S["learning"]["most_reduced"] else (["—"]+ids).index(S["learning"]["most_reduced"]))
        S["learning"]["remaining"] = st.selectbox("Most important remaining risk", options=["—"]+ids, format_func=lambda i: ("—" if i=="—" else f"{i}: {texts[i]}"), index=0 if not S["learning"]["remaining"] else (["—"]+ids).index(S["learning"]["remaining"]))
    with c2:
        S["learning"]["next_test"] = st.selectbox("Next real-world test", options=list(EXPERIMENTS.keys()), index=0 if not S["learning"]["next_test"] else list(EXPERIMENTS.keys()).index(S["learning"]["next_test"]))
        S["learning"]["success_metric"] = st.text_input("Success metric / threshold (e.g., ≥ 4% signups, ≥ 2 cards, Δ ≥ 2°F)", value=S["learning"]["success_metric"])
    S["learning"]["evidence"] = st.text_area("Evidence summary (one or two sentences)", value=S["learning"]["evidence"], height=80)

    # Show ranked list + current statuses
    st.markdown("#### Your ranked assumptions & statuses")
    df = pd.DataFrame([{
        "Rank": S["ranking_ids"].index(aid)+1,
        "ID": aid,
        "Risk": risk_label(amap[aid]["risk"]),
        "Assumption": amap[aid]["text"],
        "Status": S["assumption_status"].get(aid, "Unassessed")
    } for aid in S["ranking_ids"]])
    st.dataframe(df, hide_index=True, use_container_width=True, height=min(500, 42*len(df)+40))

    if st.button("Submit & score"):
        compute_scoring()
        S["stage"]="score"; st.rerun()

def page_score():
    st.subheader("Feedback & score")
    sc = S["score"]
    if not sc:
        st.warning("No score yet.")
        return
    st.metric("Total", f"{sc['total']}/100")
    st.markdown("#### Components (with reasons)")
    for k,v in sc["components"].items():
        label = "Excellent" if v>=80 else "Good" if v>=60 else "Needs work"
        reason = S["reasons"].get(k, "")
        st.write(f"- **{k}:** {v}/100 — {label}")
        if reason:
            st.caption(reason)

    st.markdown("#### Round recap")
    def recap(rd):
        amap = assumption_map()
        if not S[rd]["picked"]:
            return "—"
        lines=[]
        for a_id, exp in S[rd]["picked"]:
            res = S[rd]["results"].get(a_id, {})
            lines.append(f"- {a_id} ({risk_label(amap[a_id]['risk'])}) — {amap[a_id]['text']}  \n  _{exp}_ → **{res.get('metric','')}** ({res.get('verdict','')}) • Status: {S[rd]['statuses'].get(a_id,'—')}")
        return "\n".join(lines)
    with st.expander("Round 1"):
        st.markdown(recap("r1"))
    with st.expander("Round 2"):
        st.markdown(recap("r2"))
    if S["r3"]["picked"]:
        with st.expander("Round 3"):
            st.markdown(recap("r3"))

    st.markdown("#### Learning summary you entered")
    L=S["learning"]
    st.write(f"- **Reduced risk:** {L['most_reduced'] or '—'}")
    st.write(f"- **Remaining risk:** {L['remaining'] or '—'}")
    st.write(f"- **Next test:** {L['next_test'] or '—'}  • **Success metric:** {L['success_metric'] or '—'}")
    if L["evidence"]:
        st.caption(f"Evidence: {L['evidence']}")

    c1,c2 = st.columns(2)
    if c1.button("Restart Simulation"):
        init_state(); st.rerun()
    if c2.button("Back to Learning Summary"):
        S["stage"]="summary"; st.rerun()

# ───────────────────────────────────────────────────────────────────────────────
# ROUTER
# ───────────────────────────────────────────────────────────────────────────────
def main():
    try:
        st.title(TITLE); st.caption(SUB); stage_bar()
        st.progress((STAGES.index(S["stage"])+1)/len(STAGES))
        st.divider()
        # ... existing stage routing ...
    except Exception as e:
        st.error("Unexpected error in Simulation #2.")
        st.exception(e)

if __name__ == "__main__":
    main()

    st.title(TITLE)
    st.caption(SUB)
    stage_bar()
    st.progress((STAGES.index(S["stage"])+1)/len(STAGES))
    st.divider()
    if   S["stage"]=="intro":      page_intro()
    elif S["stage"]=="idea":       page_idea()
    elif S["stage"]=="rank":       page_rank()
    elif S["stage"]=="r1_select":  page_r1_select()
    elif S["stage"]=="r1_results": page_r1_results()
    elif S["stage"]=="r2_select":  page_r2_select()
    elif S["stage"]=="r2_results": page_r2_results()
    elif S["stage"]=="r3_select":  page_r3_select()
    elif S["stage"]=="r3_results": page_r3_results()
    elif S["stage"]=="summary":    page_summary()
    else:                          page_score()

main()
