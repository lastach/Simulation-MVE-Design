import math
import random
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# --------------------------------------------------------------------------------------
# Basic page setup
# --------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Simulation #2 — Designing & Running Early Experiments",
    page_icon="🧪",
    layout="wide",
)

# --------------------------------------------------------------------------------------
# Session state helpers
# --------------------------------------------------------------------------------------
def init_state():
    if "stage" not in st.session_state:
        st.session_state.stage = "intro"
    if "idea_key" not in st.session_state:
        st.session_state.idea_key = None
    if "assumptions" not in st.session_state:
        st.session_state.assumptions = []  # all assumptions for selected idea
    if "ranked" not in st.session_state:
        st.session_state.ranked = []  # ordered copy for risk priority
    if "round" not in st.session_state:
        st.session_state.round = 1
    if "tokens_total" not in st.session_state:
        st.session_state.tokens_total = 30  # TOTAL across all 3 rounds
    if "tokens_spent" not in st.session_state:
        st.session_state.tokens_spent = 0
    if "portfolio" not in st.session_state:
        # scheduled tests: round -> list[(assumption_id, exp_key)]
        st.session_state.portfolio = {1: [], 2: [], 3: []}
    if "results" not in st.session_state:
        # realized results: round -> list[dict]
        st.session_state.results = {1: [], 2: [], 3: []}
    if "ground_truth" not in st.session_state:
        # assumption_id -> true risk level (1 low, 2 med, 3 high)
        st.session_state.ground_truth = {}
    if "validation_progress" not in st.session_state:
        # cumulative validated assumptions by type
        st.session_state.validation_progress = {
            "desirability": 0,
            "feasibility": 0,
            "viability": 0,
        }

init_state()

# --------------------------------------------------------------------------------------
# Idea cards & assumptions (ThermaLoop variant shown for now)
# --------------------------------------------------------------------------------------
IDEAS = {
    "home_comfort": {
        "title": "Home Comfort Optimizer",
        "one_liner": "Smart vents + app to eliminate hot/cold rooms and reduce bills.",
        "assumptions": [
            {"id": "A1", "text": "Homeowners perceive uneven room temps as a top 3 comfort issue.", "type": "desirability"},
            {"id": "A2", "text": "≥20% of target homeowners will try a no-tools ‘one room fix’ kit.", "type": "desirability"},
            {"id": "A3", "text": "A single room kit can deliver a noticeable comfort delta in 48 hours.", "type": "feasibility"},
            {"id": "A4", "text": "BLE sensors + app can estimate room temp and airflow accurately enough.", "type": "feasibility"},
            {"id": "A5", "text": "Installed cost of starter kit ≤ $129 with ≥60% gross margin.", "type": "viability"},
            {"id": "A6", "text": "Homeowners will accept a subscription ($5–$9/mo) for seasonal tuning.", "type": "viability"},
            {"id": "A7", "text": "Return rate for the starter kit stays under 10%.", "type": "viability"},
            {"id": "A8", "text": "Install instructions can be done self-serve without pro help.", "type": "feasibility"},
        ],
        # Ground-truth risk (3=very high ⇒ harder to validate; 1=low)
        "truth": {"A1": 2, "A2": 3, "A3": 2, "A4": 1, "A5": 2, "A6": 3, "A7": 2, "A8": 1},
    }
}

# Experiment menu: key -> details
EXPERIMENTS: Dict[str, Dict] = {
    "landing": dict(
        label="Landing Page / Waitlist",
        cost=3,
        days=3,
        desc=(
            "Publish a page with clear value & CTA (e.g., ‘Join waitlist’). "
            "Drive a trickle of traffic and measure visits & signups."
        ),
        fit=["desirability", "viability"],
    ),
    "concierge": dict(
        label="Concierge Trial",
        cost=4,
        days=7,
        desc=(
            "Manually deliver the experience to 1–5 users. "
            "Observe repeat intent (‘Would you do it again next week?’)."
        ),
        fit=["desirability", "feasibility"],
    ),
    "wizard": dict(
        label="Wizard-of-Oz Prototype",
        cost=4,
        days=7,
        desc=(
            "Fake the automation behind a UI. "
            "Observe whether users reach value while the system is ‘human-backed’."
        ),
        fit=["feasibility", "desirability"],
    ),
    "preorder": dict(
        label="Pre-order / Deposit",
        cost=5,
        days=10,
        desc=(
            "Ask for a deposit or card confirmation on a concrete offer. "
            "Stronger evidence of purchase intent and price acceptance."
        ),
        fit=["viability", "desirability"],
    ),
    "expert": dict(
        label="Expert Interview",
        cost=2,
        days=2,
        desc=(
            "Structured interviews with domain experts (installers, auditors, distributors) "
            "to uncover constraints and hidden costs."
        ),
        fit=["feasibility", "viability"],
    ),
    "adsplit": dict(
        label="Ad Split Test",
        cost=4,
        days=5,
        desc=(
            "Run 2–3 ad variants to the same audience to see which message earns more qualified clicks."
        ),
        fit=["desirability"],
    ),
}

# --------------------------------------------------------------------------------------
# Utilities / navigation
# --------------------------------------------------------------------------------------
def next_stage(s: str):
    st.session_state.stage = s

def set_idea(key: str):
    """Choose idea, randomize starting assumption order, reset state."""
    st.session_state.idea_key = key
    idea = IDEAS[key]

    shuffled = idea["assumptions"].copy()
    random.shuffle(shuffled)  # ✅ randomize initial order so learner must reorder
    st.session_state.assumptions = shuffled
    st.session_state.ranked = shuffled.copy()

    st.session_state.ground_truth = idea["truth"].copy()
    st.session_state.round = 1
    st.session_state.tokens_spent = 0
    st.session_state.portfolio = {1: [], 2: [], 3: []}
    st.session_state.results = {1: [], 2: [], 3: []}
    st.session_state.validation_progress = {"desirability": 0, "feasibility": 0, "viability": 0}
    next_stage("rank")

def get_assumption(aid: str) -> dict:
    for a in st.session_state.assumptions:
        if a["id"] == aid:
            return a
    return {"id": aid, "text": aid, "type": "desirability"}

def move_item(idx: int, direction: int):
    items = st.session_state.ranked
    new_idx = idx + direction
    if 0 <= new_idx < len(items):
        items[idx], items[new_idx] = items[new_idx], items[idx]

def pool_remaining() -> int:
    return st.session_state.tokens_total - st.session_state.tokens_spent

# --------------------------------------------------------------------------------------
# Simulation engine
# --------------------------------------------------------------------------------------
def quant_for_experiment(exp_key: str, rng: random.Random) -> str:
    """Generate learner-facing quantitative result text for each experiment type."""
    if exp_key == "landing":
        visits = rng.randint(800, 1500)
        signups = rng.randint(20, 120)
        rate = round(signups / visits * 100, 1)
        return f"{visits:,} visits → {signups} sign-ups ({rate}%)."
    if exp_key == "adsplit":
        imps = rng.randint(900, 2000)
        ctr_a = round(2.8 + 2.5 * rng.random(), 1)
        ctr_b = round(ctr_a * (0.85 + 0.3 * rng.random()), 1)
        winner = "A" if ctr_a >= ctr_b else "B"
        return f"{imps:,} impressions — variant {winner} higher CTR ({ctr_a if winner=='A' else ctr_b}%)."
    if exp_key == "concierge":
        trials = rng.randint(3, 6)
        would_pay = rng.randint(max(1, trials // 2), trials)
        repeat = rng.randint(0, would_pay)
        return f"{would_pay} of {trials} would pay again; {repeat} repeated use."
    if exp_key == "preorder":
        visitors = rng.randint(120, 300)
        confirmed = rng.randint(1, 12)
        return f"{confirmed} confirmed cards from {visitors} visitors."
    if exp_key == "wizard":
        sessions = rng.randint(6, 14)
        tasks = rng.randint(max(2, sessions // 3), sessions)
        ttv = rng.randint(6, 18)
        return f"{tasks}/{sessions} tasks completed; time-to-value ≈ {ttv} min."
    if exp_key == "expert":
        experts = rng.randint(3, 6)
        converge = rng.randint(max(1, experts // 3), experts)
        return f"{experts} experts; {converge} converged on feasibility/cost drivers."
    return "—"

def synth_result_note(aid: str, ek: str, success: bool, signal: str) -> str:
    a = get_assumption(aid)
    e = EXPERIMENTS[ek]
    stem = f"**{e['label']}** — "
    if success:
        return stem + (f"strongly supports “{a['text']}”." if signal == "strong" else f"weakly supports “{a['text']}”.")
    return stem + f"did not support “{a['text']}” this round."

def simulate_result(aid: str, ek: str, rng: random.Random) -> dict:
    """Simulate a single test result, including quant, time, and cost."""
    a = get_assumption(aid)
    e = EXPERIMENTS[ek]
    risk = st.session_state.ground_truth.get(aid, 2)  # 1..3
    fit = 1 if a["type"] in e["fit"] else 0

    base_success = {3: 0.25, 2: 0.45, 1: 0.65}[risk]
    p = base_success + 0.15 * fit
    success = rng.random() < p
    signal = "strong" if success and rng.random() < (0.5 + 0.2 * fit) else ("weak" if success else "no-signal")

    quant_line = quant_for_experiment(ek, rng)
    note = synth_result_note(aid, ek, success, signal)

    return dict(
        aid=aid,
        experiment=ek,
        success=success,
        signal=signal,
        note=note,
        quant=quant_line,
        cost=e["cost"],
        days=e["days"],
        assumption_type=a["type"],
        fit=fit,
    )

def run_round(round_idx: int):
    """Run all scheduled tests in a round. Parallelism ⇒ time = max(days) in the round."""
    rng = random.Random(100 + round_idx)
    results = []
    for (aid, ek) in st.session_state.portfolio[round_idx]:
        r = simulate_result(aid, ek, rng)
        results.append(r)
        st.session_state.tokens_spent += EXPERIMENTS[ek]["cost"]
        if r["success"]:
            st.session_state.validation_progress[r["assumption_type"]] += 1
    st.session_state.results[round_idx] = results

# --------------------------------------------------------------------------------------
# Resource efficiency & scoring
# --------------------------------------------------------------------------------------
def resource_efficiency():
    """Learning-per-cost-per-time with round parallelism."""
    total_cost = sum(r["cost"] for rnd in (1, 2, 3) for r in st.session_state.results[rnd])
    total_time = sum(max([r["days"] for r in st.session_state.results[rnd]] or [0]) for rnd in (1, 2, 3))
    learning_points = sum(2 if r["signal"] == "strong" else 1 if r["signal"] == "weak" else 0
                          for rnd in (1, 2, 3) for r in st.session_state.results[rnd])
    if total_cost <= 0 or total_time <= 0:
        return 0, total_cost, total_time, learning_points, 0.0
    ratio = learning_points / (total_cost * total_time)  # higher is better
    # Scale to 0–25 points (this category now carries up to 25)
    score = min(25, round(250 * ratio, 1))
    return score, total_cost, total_time, learning_points, ratio

def compute_score() -> Tuple[int, Dict[str, int], Dict[str, str]]:
    truth = st.session_state.ground_truth
    ranked_ids = [a["id"] for a in st.session_state.ranked]
    # True riskiest three by ground truth
    true_top3 = [aid for aid, _ in sorted(truth.items(), key=lambda kv: kv[1], reverse=True)[:3]]

    # Risk Prioritization (0–25)
    hits = sum(1 for aid in ranked_ids[:3] if aid in true_top3)
    risk_prior = int(25 * (hits / 3))

    # Experiment Fit (0–25)
    total = 0
    good = 0
    for rnd in (1, 2, 3):
        for aid, ek in st.session_state.portfolio[rnd]:
            total += 1
            if get_assumption(aid)["type"] in EXPERIMENTS[ek]["fit"]:
                good += 1
    exp_fit = int(25 * (good / total)) if total else 0

    # Resource Efficiency (0–25)
    eff, total_cost, total_time, learning_points, ratio = resource_efficiency()

    # Learning Outcome (0–15): strong=2, weak=1 (cap 15)
    learn = min(15, learning_points)

    # Assumption Quality (0–10): diversity among top 5
    diversity = len(set(get_assumption(aid)["type"] for aid in ranked_ids[:5]))
    qual = 6 + (4 if diversity >= 2 else 0)

    total_score = risk_prior + exp_fit + eff + learn + qual
    if total_score > 100:
        total_score = 100

    reasons = {
        "Assumption Quality": f"Top 5 include {diversity} distinct risk types.",
        "Risk Prioritization": f"{hits}/3 of the true riskiest assumptions were in your top three.",
        "Experiment Fit": f"{good}/{total} tests matched assumption type (fit-aligned).",
        "Resource Efficiency": f"{learning_points} learning pts over {total_cost} cost & {total_time} days (ratio {ratio:.3f}).",
        "Learning Outcome": f"Signals gathered: {learning_points} (strong=2, weak=1).",
    }
    breakdown = {
        "Assumption Quality": qual,
        "Risk Prioritization": risk_prior,
        "Experiment Fit": exp_fit,
        "Resource Efficiency": eff,
        "Learning Outcome": learn,
    }
    return total_score, breakdown, reasons

# --------------------------------------------------------------------------------------
# UI widgets
# --------------------------------------------------------------------------------------
def to_badge(txt: str, color: str = "#666"):
    st.markdown(
        f"<span style='padding:2px 8px;border-radius:12px;background:{color};color:#fff;font-size:0.85rem'>{txt}</span>",
        unsafe_allow_html=True,
    )

def stepper():
    cols = st.columns(10)
    steps = [
        "Intro",
        "Choose Idea",
        "Rank Risks",
        "Round 1 — Select",
        "Round 1 — Results",
        "Round 2 — Select",
        "Round 2 — Results",
        "Round 3 — Select",
        "Round 3 — Results",
        "Learning & Score",
    ]
    idx_map = {
        "intro": 0,
        "choose": 1,
        "rank": 2,
        "r1_select": 3,
        "r1_results": 4,
        "r2_select": 5,
        "r2_results": 6,
        "r3_select": 7,
        "r3_results": 8,
        "score": 9,
    }
    active_idx = idx_map.get(st.session_state.stage, 0)
    for i, c in enumerate(cols):
        with c:
            style = (
                "background:#eef6ff;border:1px solid #cde;"
                if i == active_idx
                else "background:#f7f7f9;border:1px solid #eee;"
            )
            st.markdown(
                f"""
                <div style="{style}padding:8px 10px;border-radius:10px;text-align:center;min-height:56px">
                {steps[i]}
                </div>
                """,
                unsafe_allow_html=True,
            )

# --------------------------------------------------------------------------------------
# Screens
# --------------------------------------------------------------------------------------
def screen_intro():
    stepper()
    st.title("Simulation #2 — Designing & Running Early Experiments")
    st.caption("ThermaLoop: rank risks, pick scrappy tests, learn quickly.")
    st.subheader("What you’ll do")
    st.markdown(
        """
1) **Choose a seed idea**.  
2) **Rank** 6–10 assumptions from *riskiest to least risky*.  
3) For **three rounds**, spend from your **total token budget** to run scrappy tests.  
4) Review **quant results**, track **cumulative validation**, and iterate.  
5) See your **score** with targeted coaching notes.
"""
    )
    st.info("Tokens shown in Round 1 are your **total budget across all rounds** (not per-round).")
    st.button("Start", type="primary", on_click=lambda: next_stage("choose"))

def screen_choose():
    stepper()
    st.subheader("Pick your idea to test")
    idea = IDEAS["home_comfort"]
    st.markdown(f"### {idea['title']}")
    st.caption(idea["one_liner"])
    with st.expander("Show initial assumptions", expanded=False):
        for a in idea["assumptions"]:
            st.markdown(f"- {a['text']}  _({a['type']})_")
    st.button("Choose", key="pick_home", on_click=lambda: set_idea("home_comfort"), type="primary")

def screen_rank():
    stepper()
    st.subheader("Rank your assumptions (highest → lowest risk)")
    st.caption("Use the ▲▼ buttons to reorder. Put the **riskiest** items at the **top**.")
    items = st.session_state.ranked

    for i, a in enumerate(items):
        cols = st.columns([0.06, 0.06, 0.88])
        with cols[0]:
            st.button("▲", key=f"up_{i}", on_click=lambda idx=i: move_item(idx, -1))
        with cols[1]:
            st.button("▼", key=f"dn_{i}", on_click=lambda idx=i: move_item(idx, +1))
        with cols[2]:
            to_badge(a["type"], "#3a7")
            st.markdown(f"**{a['id']}** — {a['text']}")

    st.divider()
    st.button("Next: Round 1 — Select Tests", type="primary", on_click=lambda: next_stage("r1_select"))

def screen_round_select(round_idx: int):
    stepper()
    st.subheader(f"Round {round_idx} — Select your experiments")
    st.caption("Schedule as many tests as your **total token budget** allows. Parallel within a round; time = longest test.")

    # tokens (pool)
    remaining = pool_remaining()
    to_badge(f"Total token budget: {st.session_state.tokens_total}", "#295")
    st.write(" ")
    to_badge(f"Remaining now: {remaining}", "#295")

    # show ranked list with selector of experiments
    ranked = st.session_state.ranked
    st.markdown("##### Assumptions (your order)")
    for a in ranked:
        with st.expander(f"{a['id']} — {a['text']}", expanded=False):
            st.caption(f"Type: **{a['type']}**")
            cols = st.columns(3)
            keys = list(EXPERIMENTS.keys())
            for i, ek in enumerate(keys):
                card = EXPERIMENTS[ek]
                with cols[i % 3]:
                    st.markdown(
                        f"**{card['label']}**  \n_{card['desc']}_  \nCost: **{card['cost']}**, Duration: **{card['days']}d**"
                    )
                    if st.button(f"Add → {a['id']}", key=f"add_{round_idx}_{a['id']}_{ek}"):
                        if st.session_state.tokens_spent + card["cost"] <= st.session_state.tokens_total:
                            st.session_state.portfolio[round_idx].append((a["id"], ek))
                            st.toast(f"Added {card['label']} for {a['id']}")
                        else:
                            st.warning("Not enough total tokens remaining.")

    st.divider()
    scheduled = st.session_state.portfolio[round_idx]
    if scheduled:
        st.markdown("#### Scheduled this round")
        df = pd.DataFrame(
            [
                {"Assumption": aid, "Experiment": EXPERIMENTS[ek]["label"], "Cost": EXPERIMENTS[ek]["cost"], "Days": EXPERIMENTS[ek]["days"]}
                for (aid, ek) in scheduled
            ]
        )
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("No tests scheduled yet.")

    can_run = len(scheduled) > 0
    if can_run:
        st.button(
            f"Run Round {round_idx}",
            type="primary",
            on_click=lambda r=round_idx: (run_round(r), next_stage(f"r{r}_results")),
        )
    else:
        st.button(f"Run Round {round_idx}", disabled=True)

def screen_round_results(round_idx: int):
    stepper()
    st.subheader(f"Round {round_idx} — Results")

    res = st.session_state.results[round_idx]
    if not res:
        st.warning("No results recorded. Go back and schedule tests.")
        return

    # show each result card with quant + signal
    for r in res:
        a = get_assumption(r["aid"])
        e = EXPERIMENTS[r["experiment"]]
        box = st.container(border=True)
        with box:
            st.markdown(f"**{a['id']}** — {a['text']}")
            st.markdown(
                f"**Experiment:** {e['label']}  \n"
                f"**Outcome:** {'✅ Success' if r['success'] else '❌ No evidence'}  \n"
                f"**Signal:** {r['signal']}"
            )
            st.markdown(f"*{r['quant']}*")
            st.caption(r["note"])

    # cumulative validation progress
    st.divider()
    st.markdown("#### Cumulative Validation Progress")
    show_validation_chart()
    st.caption("Progress accumulates across rounds. Bar height = count of validated assumptions by type.")

    st.divider()
    if round_idx < 3:
        st.button("Next Round — Select", type="primary", on_click=lambda r=round_idx + 1: next_stage(f"r{r}_select"))
    else:
        st.button("See Learning Summary & Score", type="primary", on_click=lambda: next_stage("score"))

# --------------------------------------------------------------------------------------
# Scoring & Feedback screen
# --------------------------------------------------------------------------------------
def screen_score():
    stepper()
    st.subheader("Learning Summary & Score")

    total, breakdown, reasons = compute_score()

    # Show total and table with /100 aligned reasons
    st.metric("Total Score (0–100)", total)
    ordered = ["Assumption Quality", "Risk Prioritization", "Experiment Fit", "Resource Efficiency", "Learning Outcome"]
    rows = []
    weights = {"Assumption Quality": 10, "Risk Prioritization": 25, "Experiment Fit": 25, "Resource Efficiency": 25, "Learning Outcome": 15}
    for cat in ordered:
        raw = breakdown.get(cat, 0)
        out100 = round(100 * raw / weights[cat]) if weights[cat] else 0
        rows.append({"Category": cat, "Score (/100)": out100, "Why you scored this way": reasons.get(cat, "—")})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # Cumulative time & money summary
    eff_score, total_cost, total_time, learning_points, ratio = resource_efficiency()
    st.markdown("#### Cumulative Time & Money Summary")
    st.write(f"- **Total tokens spent:** {st.session_state.tokens_spent}/{st.session_state.tokens_total}")
    st.write(f"- **Total cost (token units):** {total_cost}")
    st.write(f"- **Total elapsed time:** {total_time} days (sum of the longest test each round)")
    st.write(f"- **Learning points:** {learning_points} (strong=2, weak=1)")
    if learning_points > 0:
        st.write(f"- **Avg cost per learning point:** {round(total_cost / learning_points, 2)}")
        st.write(f"- **Efficiency ratio:** {ratio:.3f} (learning / (cost × time))")

    # Coaching notes (expanded & tailored)
    st.divider()
    st.markdown("#### Coaching Notes")
    notes = []
    if breakdown["Risk Prioritization"] < 17:
        notes.append("Push **desirability** risks to the very top and probe them with cheap tests before investing elsewhere.")
    if breakdown["Experiment Fit"] < 17:
        notes.append("Tighten **test-to-assumption fit** — demand → intent tests, feasibility → workflow/latency tests, viability → price/purchase tests.")
    if eff_score < 14:
        notes.append("Shorten **time to learning** with faster/cheaper tests in Round 1. Mix landing/ads with one concierge probe.")
    if breakdown["Learning Outcome"] < 10:
        notes.append("Increase **signal strength** (e.g., pre-orders, repeat usage) instead of only directional signals.")
    diversity = len(set(get_assumption(aid)["type"] for aid in [a["id"] for a in st.session_state.ranked[:5]]))
    if diversity < 2:
        notes.append("Broaden your **assumption mix** among desirability/feasibility/viability in your top 5.")
    if pool_remaining() > 0:
        notes.append(f"You finished with **{pool_remaining()} tokens** unused. Consider reallocating to higher-signal, short-duration tests earlier.")
    if not notes:
        notes.append("Great balance. Your sequencing, fit, and efficiency look strong — this is textbook early validation.")
    for n in notes:
        st.write(f"- {n}")

    st.success("Simulation complete. Refresh to try a different idea or ranking strategy.")

# --------------------------------------------------------------------------------------
# Router
# --------------------------------------------------------------------------------------
def router():
    s = st.session_state.stage
    if s == "intro":
        screen_intro()
    elif s == "choose":
        screen_choose()
    elif s == "rank":
        screen_rank()
    elif s == "r1_select":
        screen_round_select(1)
    elif s == "r1_results":
        screen_round_results(1)
    elif s == "r2_select":
        screen_round_select(2)
    elif s == "r2_results":
        screen_round_results(2)
    elif s == "r3_select":
        screen_round_select(3)
    elif s == "r3_results":
        screen_round_results(3)
    elif s == "score":
        screen_score()
    else:
        screen_intro()

# --------------------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------------------
router()
