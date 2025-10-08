# app_sim2.py
# Simulation #2 — Designing & Running Early Experiments (ThermaLoop)
# Run: streamlit run app_sim2.py

import random
from typing import Dict, Any, List, Tuple
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Simulation #2 — Scrappy Experiments", page_icon="🧪", layout="wide")
random.seed(42)

TITLE = "Simulation #2 — Designing & Running Early Experiments"
SUB   = "ThermaLoop: pick riskiest assumptions, run scrappy tests, and learn fast"

# ───────────────────────────────────────────────────────────────────────────────
# IDEA CARDS (derived from Sim #1 “best” problem statements)
# Each assumption also carries simple TAGS to help experiment-fit & results
# Hidden_truth: 'H' (high risk), 'M', 'L' controls result bias
# ───────────────────────────────────────────────────────────────────────────────

IDEA_CARDS: Dict[str, Dict[str, Any]] = {
    "Comfort-First Home Kit (Homeowners)": {
        "desc": "Smart vent retrofit for homeowners to fix hot/cold rooms quickly and affordably.",
        "assumptions": [
            {"id":"A1","text":"Uneven room temperature is a top-3 annoyance for target homeowners.","tags":["demand","comfort"],"truth":"M"},
            {"id":"A2","text":"Homeowners will pay $200–$300 for noticeable comfort improvement even without energy savings.","tags":["wtp","pricing","comfort"],"truth":"M"},
            {"id":"A3","text":"Install can be completed in under 20 minutes by a non-expert.","tags":["install_time","feasibility"],"truth":"H"},
            {"id":"A4","text":"The device fits 90% of standard vent sizes without modification.","tags":["compat","feasibility"],"truth":"M"},
            {"id":"A5","text":"Comfort improvement is noticeable within 48 hours.","tags":["comfort","time_to_value"],"truth":"L"},
            {"id":"A6","text":"Noise from the motor is no louder than a typical fan at night.","tags":["noise","quality"],"truth":"M"},
            {"id":"A7","text":"Self-install is preferred over calling a contractor.","tags":["channel","self_install","demand"],"truth":"L"},
            {"id":"A8","text":"App setup can be completed in under 5 minutes.","tags":["onboarding","feasibility","ux"],"truth":"M"},
            {"id":"A9","text":"Customers prefer comfort gains over energy savings as the main benefit.","tags":["positioning","comfort"],"truth":"L"},
            {"id":"A10","text":"Users will share/advocate if it fixes a daily annoyance.","tags":["referral","demand"],"truth":"M"},
        ],
    },
    "Installer-Enablement System (HVAC channel)": {
        "desc": "Toolkit sold via installers to reduce callbacks and create an upsell.",
        "assumptions": [
            {"id":"B1","text":"Installers experience at least 2+ comfort-related callbacks per month.","tags":["callbacks","installer_econ"],"truth":"L"},
            {"id":"B2","text":"Reducing callbacks measurably improves NPS/reviews for installers.","tags":["callbacks","evidence"],"truth":"M"},
            {"id":"B3","text":"A 15–20% commission is enough incentive to promote the product.","tags":["commission","wtp_installer"],"truth":"M"},
            {"id":"B4","text":"Installers can learn install steps within 30 minutes after training.","tags":["training","feasibility"],"truth":"H"},
            {"id":"B5","text":"The kit adds ≤15 minutes to a typical job.","tags":["install_time","feasibility"],"truth":"M"},
            {"id":"B6","text":"Homeowners trust installer upsells for comfort solutions.","tags":["trust","channel"],"truth":"M"},
            {"id":"B7","text":"Manufacture-backed guarantee is sufficient to reduce installer risk.","tags":["warranty","risk"],"truth":"M"},
            {"id":"B8","text":"Avoiding one callback per month makes the product worthwhile.","tags":["unit_econ","roi_installer"],"truth":"M"},
            {"id":"B9","text":"Utility rebates significantly improve close rates.","tags":["rebates","viability"],"truth":"L"},
            {"id":"B10","text":"Installers will use a companion training/certification app.","tags":["training","adoption"],"truth":"M"},
        ],
    },
    "Landlord Energy Optimization Service (Property owners)": {
        "desc": "Managed subscription for landlords to reduce HVAC waste and complaints across units.",
        "assumptions": [
            {"id":"C1","text":"Landlords track heating/cooling complaints as a meaningful KPI.","tags":["complaints","ops"],"truth":"M"},
            {"id":"C2","text":"Payback under 24 months is essential for adoption.","tags":["payback","viability"],"truth":"H"},
            {"id":"C3","text":"Monthly subscription pricing is preferred over upfront purchases.","tags":["pricing_model","subscription"],"truth":"M"},
            {"id":"C4","text":"Tenants will not tamper with installed devices.","tags":["tamper","reliability"],"truth":"M"},
            {"id":"C5","text":"Bulk installs (≥10 units/day) are feasible with small teams.","tags":["deployment","feasibility"],"truth":"H"},
            {"id":"C6","text":"Property managers can act on real-time temperature alerts.","tags":["ops","alerting","activation"],"truth":"M"},
            {"id":"C7","text":"Utility rebates significantly improve ROI and adoption.","tags":["rebates","viability"],"truth":"L"},
            {"id":"C8","text":"Reduced tenant turnover is more valued than direct energy savings.","tags":["value","positioning"],"truth":"M"},
            {"id":"C9","text":"Maintenance teams can handle retrofits without third parties.","tags":["maintenance","feasibility"],"truth":"M"},
            {"id":"C10","text":"'Smart sustainability features' improve property marketing.","tags":["marketing","demand"],"truth":"L"},
        ],
    },
}

# Experiments: description + cost + tags they fit best + sample result generators
EXPERIMENTS = {
    "Landing Page Test":   {"cost":2, "fits":["demand","wtp","positioning","pricing"], "desc":"Quick page + traffic to measure message/price intent."},
    "Concierge Trial":     {"cost":3, "fits":["comfort","time_to_value","quality","ux"], "desc":"Manually deliver the service to 3–5 targets; observe behavior."},
    "Prototype Demo":      {"cost":2, "fits":["feasibility","install_time","compat","noise","onboarding"], "desc":"Lightweight mock or video walkthrough; observe usability/fit."},
    "Expert Interview":    {"cost":1, "fits":["training","ops","warranty","rebates","channel","trust"], "desc":"Interview 1–2 experts for constraints and realism."},
    "Pre-Order Test":      {"cost":3, "fits":["wtp","pricing","subscription"], "desc":"Collect soft payments or deposit intent at target price."},
    "Data Comparison":     {"cost":2, "fits":["comfort","evidence","callbacks","unit_econ","payback"], "desc":"Measure comfort/complaints/ROI vs current setup."},
}

# Round token policy
ROUND1_TOKENS = 6
TOTAL_TOKENS   = 8  # round2 adds (TOTAL - spent_in_round1). Round3 appears only if ≥2 tokens remain.

# ───────────────────────────────────────────────────────────────────────────────
# Utility
# ───────────────────────────────────────────────────────────────────────────────
def clamp(x, lo, hi): return max(lo, min(hi, x))

def fit_score(exp_name: str, assumption_tags: List[str]) -> float:
    """How well an experiment type matches an assumption's tags."""
    exp = EXPERIMENTS[exp_name]
    overlap = len(set(exp["fits"]).intersection(assumption_tags))
    return min(1.0, 0.35 + 0.2 * overlap)  # base 0.35 + 0.2 per tag overlap

def truth_bias(truth: str) -> float:
    """H: harder to validate (lower success prob), M: mixed, L: easier."""
    return {"H": 0.35, "M": 0.55, "L": 0.75}[truth]

def simulate_result(exp_name: str, assumption: Dict[str,Any]) -> Dict[str,Any]:
    """Generate a data snippet influenced by truth + fit + randomness."""
    base = truth_bias(assumption["truth"])
    fit  = fit_score(exp_name, assumption["tags"])
    p_success = clamp(0.15 + 0.6*fit*base + random.uniform(-0.08, 0.08), 0.05, 0.95)

    # A few canned metrics per experiment
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
        return {"metric": note, "verdict": verdict, "note":"Noise acceptable; manual effort high."}

    if exp_name == "Prototype Demo":
        jams = max(0, int(random.gauss(1.2 - 1.0*fit, 0.7)))
        install = round(random.uniform(12, 28) * (1.1 - 0.5*fit), 0)
        noise = round(random.uniform(30, 45) * (1.2 - 0.3*fit), 0)  # dB
        verdict = "positive" if (random.random() < p_success and jams<=1 and install<=20) else ("mixed" if jams<=2 else "negative")
        return {"metric": f"Install {install} min • jams {jams} • ~{noise} dB", "verdict": verdict, "note":"Usability observations gathered."}

    if exp_name == "Expert Interview":
        key = random.choice(["install time feasible","training curve moderate","rebate pathway promising","warranty expectation high"])
        verdict = "positive" if random.random() < p_success else "weak"
        return {"metric": f"Expert view: {key}", "verdict": verdict, "note":"Directional evidence; not a customer signal."}

    if exp_name == "Pre-Order Test":
        leads = random.randint(60, 220)
        cards = int(leads * clamp(0.03 + 0.05*(fit-0.5) + random.uniform(-0.01,0.01), 0.01, 0.12))
        verdict = "positive" if random.random() < p_success and cards>=3 else "weak"
        return {"metric": f"{leads} leads • {cards} confirmed cards", "verdict": verdict, "note":"Price sensitivity visible."}

    if exp_name == "Data Comparison":
        delta = round(random.uniform(1.0, 3.0)*(0.9+0.5*fit), 1)
        complaints = random.randint(0, max(0, int(3 - 2*fit + random.uniform(-1,1))))
        verdict = "positive" if random.random() < p_success else ("mixed" if complaints<=1 else "weak")
        return {"metric": f"Avg room Δ {delta}°F • complaints {complaints}", "verdict": verdict, "note":"Quant baseline captured."}

    return {"metric":"—","verdict":"weak","note":"Noisy read."}

# ───────────────────────────────────────────────────────────────────────────────
# APP STATE
# ───────────────────────────────────────────────────────────────────────────────
def init_state():
    st.session_state.sim2 = {
        "stage":"intro",
        "idea_key": None,
        "round1": {
            "picked": [],    # [(assumption_id, exp_name)]
            "results": {},   # assumption_id -> result dict
            "statuses": {},  # assumption_id -> Validated/Weakened/Still Risky/Invalidated
            "tokens_spent": 0
        },
        "round2": {
            "picked": [],
            "results": {},
            "statuses": {},
            "tokens_spent": 0
        },
        "round3": {
            "picked": [],
            "results": {},
            "statuses": {},
            "tokens_spent": 0
        },
        "assumption_status": {},  # global current status by assumption_id
        "learning": {
            "most_reduced": None,
            "evidence": "",
            "remaining": None,
            "next_test": None,
            "success_metric": ""
        },
        "score": None,
        "coaching": {},
    }
if "sim2" not in st.session_state:
    init_state()
S = st.session_state.sim2

# ───────────────────────────────────────────────────────────────────────────────
# STAGE BAR
# ───────────────────────────────────────────────────────────────────────────────
STAGES = [
    "intro","idea","r1_select","r1_results","r2_select","r2_results","r3_select","r3_results","summary","score"
]
LABELS = {
    "intro":"Intro",
    "idea":"Choose Idea",
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
        cur_i = STAGES.index(S["stage"])
        prefix = "✅ " if i < cur_i else ("👉 " if i == cur_i else "")
        if cols[i].button(f"{prefix}{LABELS[k]}", key=f"nav_{k}"):
            # allow only backward nav
            if i <= cur_i:
                S["stage"] = k
                st.rerun()

# ───────────────────────────────────────────────────────────────────────────────
# HELPERS
# ───────────────────────────────────────────────────────────────────────────────
def get_idea() -> Dict[str,Any]:
    return IDEA_CARDS[S["idea_key"]] if S["idea_key"] else None

def assumptions_df(idea_key: str) -> pd.DataFrame:
    rows=[]
    for a in IDEA_CARDS[idea_key]["assumptions"]:
        status = S["assumption_status"].get(a["id"], "Unassessed")
        rows.append({"ID":a["id"], "Assumption":a["text"], "Status":status})
    return pd.DataFrame(rows)

def tokens_remaining() -> int:
    spent = S["round1"]["tokens_spent"] + S["round2"]["tokens_spent"] + S["round3"]["tokens_spent"]
    return TOTAL_TOKENS - spent

def tokens_used_in_round(round_key:str) -> int:
    return S[round_key]["tokens_spent"]

def add_pick(round_key:str, a_id:str, exp_name:str):
    cost = EXPERIMENTS[exp_name]["cost"]
    if round_key=="round1":
        cap = ROUND1_TOKENS
    else:
        cap = tokens_remaining() + tokens_used_in_round(round_key)  # this round can use what's left
    if tokens_used_in_round(round_key) + cost > cap:
        return False, f"Not enough tokens in this round. Cost {cost}, available {cap - tokens_used_in_round(round_key)}."
    S[round_key]["picked"].append((a_id, exp_name))
    S[round_key]["tokens_spent"] += cost
    return True, "Added."

def run_round(round_key:str):
    idea = get_idea()
    for a_id, exp_name in S[round_key]["picked"]:
        a = next(a for a in idea["assumptions"] if a["id"]==a_id)
        S[round_key]["results"][a_id] = simulate_result(exp_name, a)

# ───────────────────────────────────────────────────────────────────────────────
# SCORING
# ───────────────────────────────────────────────────────────────────────────────
def compute_scoring():
    idea = get_idea()
    if not idea: return
    # Map truth for prioritization checks
    truth_map = {a["id"]:a["truth"] for a in idea["assumptions"]}
    tags_map  = {a["id"]:a["tags"]  for a in idea["assumptions"]}

    # Assumption Clarity: these are pre-written testable; give base, add for breadth
    clarity = 0.8
    # If user interacted with at least 5 distinct assumptions across rounds, bump
    tested_ids = set([a for a,_ in S["round1"]["picked"]] + [a for a,_ in S["round2"]["picked"]] + [a for a,_ in S["round3"]["picked"]])
    if len(tested_ids) >= 4: clarity += 0.1
    clarity = clamp(clarity, 0, 1)
    clarity_score = int(100*clarity)

    # Risk Prioritization: reward picking H risks in R1, then M
    r1_ids = [a for a,_ in S["round1"]["picked"]]
    r2_ids = [a for a,_ in S["round2"]["picked"]]
    r3_ids = [a for a,_ in S["round3"]["picked"]]
    def weight(t): return {"H":1.0,"M":0.6,"L":0.2}[t]
    r1 = sum(weight(truth_map[i]) for i in r1_ids) / max(1, len(r1_ids))
    r2 = sum(weight(truth_map[i]) for i in r2_ids) / max(1, len(r2_ids))
    prioritization = clamp(0.65*r1 + 0.35*r2, 0, 1)
    prioritization_score = int(100*prioritization)

    # Experiment Fit: average fit of selected pairs
    def avg_fit(picks):
        if not picks: return 0
        vals = []
        for a_id, exp in picks:
            vals.append(fit_score(exp, tags_map[a_id]))
        return sum(vals)/len(vals)
    fit_avg = clamp(0.5*avg_fit(S["round1"]["picked"]) + 0.5*avg_fit(S["round2"]["picked"] + S["round3"]["picked"]), 0, 1)
    fit_score_val = int(100*fit_avg)

    # Resource Efficiency: tokens spent <= TOTAL, diversity, and some carryover before R3
    spent_total = S["round1"]["tokens_spent"] + S["round2"]["tokens_spent"] + S["round3"]["tokens_spent"]
    diversity = len(set(exp for _,exp in S["round1"]["picked"] + S["round2"]["picked"] + S["round3"]["picked"]))
    eff = 0.0
    if spent_total <= TOTAL_TOKENS: eff += 0.6
    if diversity >= 3: eff += 0.25
    if S["round3"]["picked"] and tokens_remaining() >= 0: eff += 0.15
    eff = clamp(eff, 0, 1)
    efficiency_score = int(100*eff)

    # Learning Outcome: did they update statuses consistent with results bias?
    def status_points(rd):
        pts = 0; n=0
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
    learn = clamp(0.6*status_points("round1") + 0.4*status_points("round2"), 0, 1)
    if S["round3"]["picked"]:
        learn = clamp(0.5*status_points("round2") + 0.5*status_points("round3"), 0, 1)
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

    # Coaching (actionable)
    notes = {}
    if prioritization < 0.65:
        notes["Risk Prioritization"] = "Address the highest-risk assumptions first. In Round 1, prefer items marked as hardest to satisfy (e.g., install time ≤ 20 min)."
    if fit_avg < 0.65:
        notes["Experiment Fit"] = "Match tests to risks: pricing/intent → Landing or Pre-order; feasibility (install/compat/noise) → Prototype Demo; ROI/callbacks → Data Comparison or Concierge."
    if eff < 0.7:
        notes["Resource Efficiency"] = "Aim for 2–3 distinct experiment types and keep total spend ≤ token cap. Avoid repeating the same signal twice."
    if learning_score < 0.7:
        notes["Learning Outcome"] = "Translate results to decisions: mark validated/invalidated and pick a next test that targets what remains uncertain."

    S["coaching"] = notes

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
1) Choose a direction (**Idea Card**) with pre-listed assumptions.  
2) **Round 1:** Pick **1–2 riskiest assumptions** and a scrappy **experiment** for each (≤ 6 tokens).  
3) Review **results** and update **risk statuses**.  
4) **Round 2:** See all assumptions again; pick **2–3** more tests within remaining tokens (**8 total**).  
5) Optional **Round 3** appears if you still have ≥ 2 tokens.  
6) Complete a short **Learning Summary** → **Score & coaching**.
""")
    if st.button("Start"):
        S["stage"]="idea"; st.rerun()

def page_idea():
    st.subheader("Choose your idea card")
    cols = st.columns(3)
    keys = list(IDEA_CARDS.keys())
    for i,k in enumerate(keys):
        with cols[i]:
            st.markdown(f"**{k}**")
            st.caption(IDEA_CARDS[k]["desc"])
            df = pd.DataFrame([{"Assumption":a["text"]} for a in IDEA_CARDS[k]["assumptions"]])
            st.dataframe(df, use_container_width=True, hide_index=True, height=min(300, 40*len(df)+30))
            if st.button(f"Work on this", key=f"pick_{k}"):
                S["idea_key"]=k
                # reset statuses
                S["assumption_status"] = {a["id"]:"Unassessed" for a in IDEA_CARDS[k]["assumptions"]}
                S["stage"]="r1_select"; st.rerun()

def render_round_selector(round_key:str, max_picks:int, note:str, token_cap:int):
    st.markdown(f"**Token cap for this round:** {token_cap}")
    idea = get_idea()
    assumps = idea["assumptions"]
    df = assumptions_df(S["idea_key"])
    st.dataframe(df, use_container_width=True, hide_index=True, height=min(400, 40*len(df)+30))
    st.info(note)

    # Selection UI
    available_ids = [a["id"] for a in assumps]
    picks_local: List[Tuple[str,str]] = S[round_key]["picked"][:]
    cost_spent = S[round_key]["tokens_spent"]

    # Add pickers
    c1,c2,c3 = st.columns([2,2,1])
    with c1:
        a_id = st.selectbox("Assumption", options=available_ids, format_func=lambda i: next(a["text"] for a in assumps if a["id"]==i))
    with c2:
        exp_name = st.selectbox("Experiment", options=list(EXPERIMENTS.keys()), format_func=lambda x: f"{x} (cost {EXPERIMENTS[x]['cost']})")
    with c3:
        if st.button("Add"):
            if (a_id, exp_name) in picks_local:
                st.warning("Already added.")
            elif len(picks_local) >= max_picks:
                st.warning(f"Limit reached: {max_picks} picks this round.")
            else:
                ok,msg = add_pick(round_key, a_id, exp_name)
                if ok:
                    st.success("Added.")
                else:
                    st.warning(msg)
                st.rerun()

    # Show current portfolio
    st.markdown("**Selected this round**")
    if S[round_key]["picked"]:
        for a_id, exp in S[round_key]["picked"]:
            st.write(f"- {a_id}: {next(a['text'] for a in assumps if a['id']==a_id)}  \n  _{exp} • cost {EXPERIMENTS[exp]['cost']} • fit ~{int(100*fit_score(exp, next(a['tags'] for a in assumps if a['id']==a_id)))}%_")
    else:
        st.caption("Nothing selected yet.")
    st.metric("Tokens spent", f"{S[round_key]['tokens_spent']}/{token_cap}")

def page_r1_select():
    st.subheader("Round 1 — choose your riskiest assumptions & tests")
    render_round_selector("round1", max_picks=2, note="Pick 1–2 riskiest items and match a test that best reduces uncertainty.", token_cap=ROUND1_TOKENS)
    c1,c2 = st.columns(2)
    if c1.button("Back"):
        S["stage"]="idea"; st.rerun()
    if c2.button("Run Round 1"):
        if len(S["round1"]["picked"])<1:
            st.warning("Pick at least one assumption to test.")
        else:
            run_round("round1")
            S["stage"]="r1_results"; st.rerun()

def render_round_results(round_key:str):
    st.markdown("**Results**")
    idea = get_idea()
    for a_id, exp in S[round_key]["picked"]:
        a = next(a for a in idea["assumptions"] if a["id"]==a_id)
        res = S[round_key]["results"][a_id]
        with st.container(border=True):
            st.write(f"**{a_id} — {a['text']}**")
            st.caption(f"Experiment: {exp} • cost {EXPERIMENTS[exp]['cost']}")
            st.write(f"**Data:** {res['metric']}")
            st.caption(res["note"])
            # status selector
            st.selectbox("Mark status", ["Validated","Weakened","Still Risky","Invalidated"],
                         key=f"status_{round_key}_{a_id}",
                         index=["Validated","Weakened","Still Risky","Invalidated"].index(S[round_key]["statuses"].get(a_id, "Still Risky")))
            S[round_key]["statuses"][a_id] = st.session_state[f"status_{round_key}_{a_id}"]

    # propagate latest statuses to global
    for a_id, stt in S[round_key]["statuses"].items():
        S["assumption_status"][a_id] = stt

def page_r1_results():
    st.subheader("Round 1 — results & status updates")
    render_round_results("round1")
    c1,c2 = st.columns(2)
    if c1.button("Back to selection"):
        S["stage"]="r1_select"; st.rerun()
    if c2.button("Proceed to Round 2"):
        S["stage"]="r2_select"; st.rerun()

def page_r2_select():
    st.subheader("Round 2 — pick next tests")
    rem = tokens_remaining()
    token_cap_for_round = rem + S["round2"]["tokens_spent"]
    render_round_selector("round2", max_picks=3, note="Choose 2–3 items (including unresolved from Round 1). You have 8 total tokens across rounds.", token_cap=token_cap_for_round)
    if tokens_remaining() >= 2:
        st.caption("If ≥ 2 tokens remain after Round 2, Round 3 will unlock.")
    c1,c2 = st.columns(2)
    if c1.button("Back to Round 1 results"):
        S["stage"]="r1_results"; st.rerun()
    if c2.button("Run Round 2"):
        if len(S["round2"]["picked"])<1:
            st.warning("Pick at least one assumption to test.")
        else:
            run_round("round2")
            S["stage"]="r2_results"; st.rerun()

def page_r2_results():
    st.subheader("Round 2 — results & status updates")
    render_round_results("round2")
    c1,c2,c3 = st.columns(3)
    # Round 3 unlock check
    if tokens_remaining() >= 2:
        if c1.button("Proceed to Round 3"):
            S["stage"]="r3_select"; st.rerun()
    if c2.button("Back to Round 2 selection"):
        S["stage"]="r2_select"; st.rerun()
    if c3.button("Skip to Learning Summary"):
        S["stage"]="summary"; st.rerun()

def page_r3_select():
    st.subheader("Round 3 — optional big bet")
    rem = tokens_remaining()
    if rem < 2:
        st.info("Not enough tokens for Round 3. Move to Learning Summary.")
    token_cap_for_round = rem + S["round3"]["tokens_spent"]
    render_round_selector("round3", max_picks=1, note="Choose one high-impact test if you have ≥ 2 tokens remaining.", token_cap=token_cap_for_round)
    c1,c2 = st.columns(2)
    if c1.button("Back to Round 2 results"):
        S["stage"]="r2_results"; st.rerun()
    if c2.button("Run Round 3"):
        if len(S["round3"]["picked"])<1:
            st.warning("Pick an item or go back.")
        else:
            run_round("round3")
            S["stage"]="r3_results"; st.rerun()

def page_r3_results():
    st.subheader("Round 3 — results & status updates")
    render_round_results("round3")
    c1,c2 = st.columns(2)
    if c1.button("Back to Round 3 selection"):
        S["stage"]="r3_select"; st.rerun()
    if c2.button("Proceed to Learning Summary"):
        S["stage"]="summary"; st.rerun()

def page_summary():
    st.subheader("Learning summary & next steps")
    idea = get_idea()
    ids = [a["id"] for a in idea["assumptions"]]
    texts = {a["id"]:a["text"] for a in idea["assumptions"]}
    # structured fields
    c1,c2 = st.columns(2)
    with c1:
        S["learning"]["most_reduced"] = st.selectbox("Top risk you reduced", options=["—"]+ids,
                                                     format_func=lambda i: ("—" if i=="—" else f"{i}: {texts[i]}"),
                                                     index=0 if not S["learning"]["most_reduced"] else (["—"]+ids).index(S["learning"]["most_reduced"]))
        S["learning"]["remaining"] = st.selectbox("Most important remaining risk", options=["—"]+ids,
                                                  format_func=lambda i: ("—" if i=="—" else f"{i}: {texts[i]}"),
                                                  index=0 if not S["learning"]["remaining"] else (["—"]+ids).index(S["learning"]["remaining"]))
    with c2:
        S["learning"]["next_test"] = st.selectbox("Next real-world test you’d run", options=list(EXPERIMENTS.keys()),
                                                  index=0 if not S["learning"]["next_test"] else list(EXPERIMENTS.keys()).index(S["learning"]["next_test"]))
        S["learning"]["success_metric"] = st.text_input("Success metric / threshold (e.g., ≥ 4% signups, ≥ 2 cards, Δ ≥ 2°F)", value=S["learning"]["success_metric"])

    S["learning"]["evidence"] = st.text_area("Evidence summary (one or two sentences)", value=S["learning"]["evidence"], height=80)

    # simple heatmap-like table
    st.markdown("#### Assumptions & current status")
    df = assumptions_df(S["idea_key"])
    st.dataframe(df, use_container_width=True, hide_index=True, height=min(400, 40*len(df)+30))

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
    st.markdown("#### Components")
    for k,v in sc["components"].items():
        label = "Excellent" if v>=80 else "Good" if v>=60 else "Needs work"
        st.write(f"- **{k}:** {v}/100 — {label}")

    st.markdown("#### Coaching notes")
    if S["coaching"]:
        for k,v in S["coaching"].items():
            st.write(f"- **{k}:** {v}")
    else:
        st.write("Solid choices and sequencing. Keep going!")

    st.markdown("#### Your selections recap")
    idea = get_idea()
    texts = {a["id"]:a["text"] for a in idea["assumptions"]}
    def list_round(rd):
        if not S[rd]["picked"]:
            return "—"
        return "\n".join([f"- {a_id}: {texts[a_id]}  \n  _{exp}_ → **{S[rd]['results'].get(a_id,{}).get('metric','')}** ({S[rd]['results'].get(a_id,{}).get('verdict','')}) • Status: {S[rd]['statuses'].get(a_id,'—')}" for a_id,exp in S[rd]["picked"]])
    with st.expander("Round 1"):
        st.markdown(list_round("round1"))
    with st.expander("Round 2"):
        st.markdown(list_round("round2"))
    if S["round3"]["picked"]:
        with st.expander("Round 3"):
            st.markdown(list_round("round3"))

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
    header()
    if   S["stage"]=="intro":       page_intro()
    elif S["stage"]=="idea":        page_idea()
    elif S["stage"]=="r1_select":   page_r1_select()
    elif S["stage"]=="r1_results":  page_r1_results()
    elif S["stage"]=="r2_select":   page_r2_select()
    elif S["stage"]=="r2_results":  page_r2_results()
    elif S["stage"]=="r3_select":   page_r3_select()
    elif S["stage"]=="r3_results":  page_r3_results()
    elif S["stage"]=="summary":     page_summary()
    else:                           page_score()

main()
