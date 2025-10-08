# Simulation #2 — Designing & Running Early Experiments (ThermaLoop)
# ==================================================================
# Learners pick an idea, rank risks, run scrappy experiments across 3 rounds,
# and get coaching feedback with reasons per category.

import random
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple
import pandas as pd
import streamlit as st

# ---- Optional drag-and-drop (falls back to numeric ranking if unavailable) ----
try:
    from streamlit_dnd_list import dnd_list
except Exception:
    dnd_list = None

# ==============================================================================
# Config & Data
# ==============================================================================

st.set_page_config(page_title="Simulation #2 — ThermaLoop", page_icon="🧪", layout="wide")

# Round token budgets (you can tweak these)
ROUND_BUDGET = {"r1": 12, "r2": 10, "r3": 8}

# Experiment catalog (name, cost, description, tags_for_fit, signal_strength 1–3)
EXPERIMENTS: List[Tuple[str, int, str, List[str], int]] = [
    ("Landing Page Test", 3,
     "Publish a simple page with a clear promise; send small traffic to measure click-through and email signups.",
     ["desirability"], 2),
    ("Smoke Test (Reserve Now)", 4,
     "Offer a ‘Reserve Now’ / ‘Join Waitlist’ with light friction to test real intent.",
     ["desirability", "viability"], 3),
    ("Concierge Trial", 4,
     "Manually deliver the value for a handful of users (no code) and observe outcomes and willingness to continue.",
     ["desirability", "feasibility"], 2),
    ("Wizard-of-Oz Prototype", 4,
     "Fake the backend but show a real UI; validate that the flow and output meet expectations.",
     ["feasibility", "desirability"], 2),
    ("Pre-Order Test", 4,
     "Collect card-on-file or deposits (refundable) to measure true willingness to pay.",
     ["viability", "desirability"], 3),
    ("Ad Split Test", 3,
     "Run tiny-budget ads with different messages to learn what attracts attention from your segment.",
     ["desirability"], 1),
    ("Expert Interview", 2,
     "Short calls with domain experts to surface blockers (compliance, installation, supply-chain).",
     ["feasibility", "viability"], 1),
    ("Diary / Usage Log", 3,
     "Have users log behaviors for 1–2 weeks; discover triggers, frequency and sticking points.",
     ["desirability"], 2),
]

# Three idea cards; each assumption has a short tag for *internal* fit logic.
IDEA_CARDS = {
    "homeowners": {
        "title": "Homeowner: Comfort & Energy",
        "assumptions": [
            ("Main motivation is saving money, not comfort.", "desirability"),
            ("Homeowners will try a 14-day free trial.", "desirability"),
            ("Self-install can be done in under 45 minutes.", "feasibility"),
            ("Users will allow data collection from the thermostat.", "viability"),
            ("Monthly price under $9 is acceptable.", "viability"),
            ("Comfort improvement is noticeable within 7 days.", "desirability"),
            ("Mobile notifications drive weekly action.", "desirability"),
            ("Household members will not object to auto-scheduling.", "desirability"),
            ("Data privacy copy is sufficient to build trust.", "viability"),
            ("Geofencing works reliably across devices.", "feasibility"),
        ],
        # hidden “ground truth” relative risk (0 = low, 1 = high) to bias results
        "risk_truth": [0.8, 0.7, 0.6, 0.5, 0.7, 0.5, 0.4, 0.6, 0.6, 0.5],
    },
    "landlords": {
        "title": "Small Landlords: Portfolio Savings",
        "assumptions": [
            ("Property managers will share thermostat data per unit.", "viability"),
            ("Premium $49/month tier is viable.", "viability"),
            ("Main value is fewer maintenance visits (not energy).", "desirability"),
            ("80% activation within two weeks is achievable.", "feasibility"),
            ("Tenants will not disable automations.", "desirability"),
            ("PM partnerships can drive warm leads.", "desirability"),
            ("Bulk onboarding tools reduce setup time by 50%.", "feasibility"),
            ("Annual contracts with 30-day pilot are acceptable.", "viability"),
        ],
        "risk_truth": [0.7, 0.6, 0.7, 0.5, 0.6, 0.5, 0.5, 0.6],
    },
    "installers": {
        "title": "HVAC Installers: Smart Upsell",
        "assumptions": [
            ("Installers accept a 20% revenue share.", "viability"),
            ("Techs can demo the app in under 5 minutes on site.", "feasibility"),
            ("Customers approve data collection at install time.", "viability"),
            ("Comfort-focused pitch converts better than savings-first.", "desirability"),
            ("Lead routing from installer CRM is feasible without deep integration.", "feasibility"),
            ("Post-install follow-ups lift attach rate by 30%.", "desirability"),
            ("No-code internal tool is enough for scheduling and support.", "feasibility"),
        ],
        "risk_truth": [0.6, 0.5, 0.6, 0.6, 0.5, 0.5, 0.4],
    },
}

# ==============================================================================
# Utilities & State
# ==============================================================================

def init_state():
    if "stage" in st.session_state:
        return
    st.session_state.stage = "intro"
    st.session_state.idea_key = None
    st.session_state.rank_order: List[int] = []  # indices into assumptions
    st.session_state.tokens = {"r1": ROUND_BUDGET["r1"], "r2": ROUND_BUDGET["r2"], "r3": ROUND_BUDGET["r3"]}
    st.session_state.portfolio = {"r1": [], "r2": [], "r3": []}  # list of dicts {assumption, tag, exp_name, cost}
    st.session_state.results = {"r1": [], "r2": [], "r3": []}    # list of dicts {assumption, exp_name, success, details}
    st.session_state.scoring = {}
    st.session_state.log = []  # tiny audit trail for reasons text

def goto(stage: str):
    st.session_state.stage = stage
    st.experimental_rerun()

def stage_header(active_idx: int):
    tabs = ["Intro", "Choose Idea", "Rank Risks", "Round 1 — Select", "Round 1 — Results",
            "Round 2 — Select", "Round 2 — Results", "Round 3 — Select", "Round 3 — Results",
            "Learning Summary", "Feedback & Score"]
    cols = st.columns(len(tabs))
    for i, label in enumerate(tabs):
        with cols[i]:
            st.button(("✅ " if i == active_idx else "") + label, disabled=True if i == active_idx else False)

def tokens_left(round_key: str) -> int:
    return st.session_state.tokens[round_key]

# ==============================================================================
# Pages
# ==============================================================================

def page_intro():
    stage_header(0)
    st.title("Simulation #2 — Designing & Running Early Experiments")
    st.caption("ThermaLoop: rank risks, pick scrappy tests, learn quickly.")
    st.markdown("""
**You will:**
1. **Choose** an idea focus (Homeowners, Landlords, or Installers)  
2. **Rank** assumptions from *highest → lowest* risk  
3. Run scrappy experiments over **3 rounds** using your token budget  
4. Review **learning** and receive **scoring + coaching** (with reasons)

**Tokens & costs:** Each round gives you tokens. Each experiment costs 2–4 tokens.  
Use as many experiments per round as your budget allows.
""")
    if st.button("Start"):
        goto("idea")

def page_choose_idea():
    stage_header(1)
    st.subheader("Choose your idea focus")
    cols = st.columns(len(IDEA_CARDS))
    for (key, card), c in zip(IDEA_CARDS.items(), cols):
        with c:
            st.markdown(f"**{card['title']}**")
            with st.expander("See sample assumptions"):
                for a, _tag in card["assumptions"]:
                    st.write("•", a)
            if st.button("Select", key=f"select_{key}"):
                st.session_state.idea_key = key
                st.session_state.rank_order = list(range(len(card["assumptions"])))
                goto("rank")

def page_rank():
    stage_header(2)
    st.subheader("Rank your assumptions (highest → lowest risk)")
    key = st.session_state.idea_key
    if not key:
        st.info("Pick an idea first.")
        return
    assumptions = IDEA_CARDS[key]["assumptions"]
    labels = [f"{i+1}. {a[0]}" for i, a in enumerate(assumptions)]

    if dnd_list is not None:
        st.caption("Drag to reorder (top = riskiest).")
        reordered = dnd_list(labels, direction="vertical", draggable=True)
        if reordered:
            order = [int(label.split(".")[0]) - 1 for label in reordered]
            st.session_state.rank_order = order
    else:
        st.info("Drag-and-drop not available; rank them with numbers:")
        ranks = {}
        for i, (txt, _tag) in enumerate(assumptions):
            ranks[i] = st.number_input(txt, min_value=1, max_value=len(assumptions), value=i+1, key=f"rank_{i}")
        st.session_state.rank_order = [k for k, _ in sorted(ranks.items(), key=lambda kv: kv[1])]

    st.divider()
    col_l, col_r = st.columns([2,1])
    with col_l:
        st.write("**Your order:**")
        for idx in st.session_state.rank_order:
            st.write("•", assumptions[idx][0])
    with col_r:
        if st.button("Proceed to Round 1"):
            goto("r1_select")

def experiment_card(round_key: str, ass_idx: int, a_text: str, a_tag: str):
    """Render experiment options for a single assumption."""
    for name, cost, desc, tags, strength in EXPERIMENTS:
        fits = "✅ Best fit" if a_tag in tags else "OK fit"
        disabled = (tokens_left(round_key) < cost)
        key = f"{round_key}_{ass_idx}_{name}"
        with st.container(border=True):
            st.markdown(f"**{name}**  ·  Cost: **{cost}**  ·  {fits}")
            st.caption(desc)
            clicked = st.button(f"Add to plan ({cost} tokens)", disabled=disabled, key=key)
            if clicked:
                if tokens_left(round_key) >= cost:
                    st.session_state.tokens[round_key] -= cost
                    st.session_state.portfolio[round_key].append({
                        "ass_idx": ass_idx, "assumption": a_text, "tag": a_tag,
                        "exp_name": name, "cost": cost, "fit": a_tag in tags, "strength": strength
                    })
                    st.session_state.log.append(f"Added {name} on '{a_text}' in {round_key} (cost {cost}).")

def sidebar_plan(round_key: str):
    with st.sidebar:
        st.markdown(f"### {round_key.upper()} Plan")
        st.write(f"Tokens left: **{tokens_left(round_key)}**")
        if not st.session_state.portfolio[round_key]:
            st.caption("No experiments yet.")
        else:
            for i, itm in enumerate(st.session_state.portfolio[round_key], 1):
                st.write(f"{i}. {itm['exp_name']} → _{itm['assumption']}_ (cost {itm['cost']})")
            if st.button("Clear round plan", key=f"clear_{round_key}"):
                refund = sum(itm["cost"] for itm in st.session_state.portfolio[round_key])
                st.session_state.tokens[round_key] += refund
                st.session_state.portfolio[round_key].clear()

def page_round_select(round_key: str, active_header_idx: int, next_stage: str):
    stage_header(active_header_idx)
    key = st.session_state.idea_key
    assumptions = IDEA_CARDS[key]["assumptions"]
    order = st.session_state.rank_order

    st.subheader(f"{round_key.upper()} — Select Experiments")
    st.write(f"Use your tokens (**{tokens_left(round_key)}** available) to add as many tests as you like.")

    sidebar_plan(round_key)

    # Show assumptions in the learner's risk order
    for ass_rank, idx in enumerate(order, 1):
        a_text, a_tag = assumptions[idx]
        with st.expander(f"#{ass_rank}  {a_text}", expanded=(ass_rank <= 2)):
            experiment_card(round_key, idx, a_text, a_tag)

    st.divider()
    col1, col2 = st.columns([1,1])
    if col1.button("Run selected tests"):
        run_round(round_key)
        goto(next_stage)
    col2.caption("Tip: Add multiple tests; you’ll learn faster than a single bet.")

def success_probability(idea_key: str, ass_idx: int, fit: bool, strength: int, rank_position: int) -> float:
    """
    Compute a semi-realistic success probability:
    - Higher ground-truth risk → lower success
    - Better fit + stronger test → higher success
    - Earlier rank positions are riskier → slightly lower base
    """
    truth = IDEA_CARDS[idea_key]["risk_truth"][ass_idx]  # 0..1 (high = risky)
    base = 0.55 - 0.25 * truth  # 0.3 .. 0.55
    base -= 0.05 * (0.2 * rank_position)  # top-ranked assumptions are harder
    if fit:
        base += 0.12
    base += 0.06 * (strength - 1)  # +0 / +0.06 / +0.12
    return max(0.05, min(0.90, base))

def run_round(round_key: str):
    idea = st.session_state.idea_key
    order = st.session_state.rank_order
    out = []
    for itm in st.session_state.portfolio[round_key]:
        rank_pos = order.index(itm["ass_idx"]) + 1
        p = success_probability(idea, itm["ass_idx"], itm["fit"], itm["strength"], rank_pos)
        success = random.random() < p
        detail = random.choice([
            "Strong positive signal (quotes + conversion)",
            "Moderate interest; conversion below target",
            "Mixed feedback; unclear value articulation",
            "Low signal; likely invalid"
        ])
        out.append({
            "Assumption": itm["assumption"],
            "Experiment": itm["exp_name"],
            "Success": success,
            "Detail": detail,
            "RankPos": rank_pos,
            "Fit": "Good" if itm["fit"] else "OK",
            "Strength": itm["strength"],
            "Cost": itm["cost"]
        })
    st.session_state.results[round_key] = out
    st.session_state.log.append(f"Ran {len(out)} tests in {round_key}.")

def page_round_results(round_key: str, active_header_idx: int, next_stage: str, label: str):
    stage_header(active_header_idx)
    st.subheader(label)
    data = st.session_state.results[round_key]
    if not data:
        st.info("No tests were run.")
    else:
        st.dataframe(pd.DataFrame(data), hide_index=True, use_container_width=True)
        success_rate = sum(1 for r in data if r["Success"]) / len(data) if data else 0
        st.write(f"Success rate: **{success_rate:.0%}**  ·  Spent tokens: **{sum(d['Cost'] for d in data)}**")
    if st.button("Next"):
        goto(next_stage)

def page_learning():
    stage_header(9)
    st.subheader("Learning Summary")
    all_rows = st.session_state.results["r1"] + st.session_state.results["r2"] + st.session_state.results["r3"]
    if not all_rows:
        st.info("You have no results yet.")
        return
    df = pd.DataFrame(all_rows)
    st.dataframe(df, hide_index=True, use_container_width=True)

    # quick roll-ups
    by_assumption = df.groupby("Assumption")["Success"].agg(["count", "mean"]).reset_index()
    by_assumption.rename(columns={"count": "tests", "mean": "success_rate"}, inplace=True)
    st.markdown("#### Per-assumption roll-up")
    st.dataframe(by_assumption, hide_index=True, use_container_width=True)

    if st.button("View Feedback & Score"):
        calc_score()
        goto("score")

# ==============================================================================
# Scoring with reasons
# ==============================================================================

def calc_score():
    idea = st.session_state.idea_key
    assumptions = IDEA_CARDS[idea]["assumptions"]
    order = st.session_state.rank_order

    # Coverage of top risks in early rounds
    r1_targets = [r["Assumption"] for r in st.session_state.results["r1"]]
    top3_texts = [assumptions[i][0] for i in order[:3]]
    coverage = len([t for t in r1_targets if t in top3_texts]) / max(1, len(top3_texts))  # 0..1

    # Experiment Fit (how many “Good” fits, weighted by strength)
    all_rows = st.session_state.results["r1"] + st.session_state.results["r2"] + st.session_state.results["r3"]
    if all_rows:
        fit_points = sum((1.0 if r["Fit"] == "Good" else 0.6) * (1 + 0.3 * (r["Strength"] - 1)) for r in all_rows)
        fit_pct = fit_points / len(all_rows)  # ~0.6..1.3
        fit_pct = min(1.0, fit_pct / 1.0)
    else:
        fit_pct = 0.0

    # Resource efficiency (spend early, save some for later; don’t leave many tokens idle)
    spent = {}
    idle = 0
    for rk in ["r1", "r2", "r3"]:
        spent[rk] = sum(itm["Cost"] for itm in st.session_state.portfolio[rk])
        idle += st.session_state.tokens[rk]
    early_bias = min(1.0, (spent["r1"] + 0.5 * spent["r2"]) / max(1, sum(spent.values())))
    efficiency = max(0.0, 1.0 - (idle / (ROUND_BUDGET["r1"] + ROUND_BUDGET["r2"] + ROUND_BUDGET["r3"])) * 0.8)
    resource_score = 0.6 * early_bias + 0.4 * efficiency

    # Learning outcome (success rate + diversity)
    if all_rows:
        sr = sum(1 for r in all_rows if r["Success"]) / len(all_rows)
        diversity = len(set(r["Assumption"] for r in all_rows)) / max(1, len(assumptions))
        learning = 0.6 * sr + 0.4 * diversity
    else:
        learning = 0.0

    # Assumption Quality proxy (did they actually rank & hit top risks)
    quality = 0.5 + 0.5 * coverage

    def pct(x):  # to 0..100
        return int(100 * max(0.0, min(1.0, x)))

    st.session_state.scoring = {
        "Assumption Quality": pct(quality),
        "Risk Prioritization": pct(coverage),
        "Experiment Fit": pct(fit_pct),
        "Resource Efficiency": pct(resource_score),
        "Learning Outcome": pct(learning),
    }
    st.session_state.scoring["Total"] = int(
        0.30 * st.session_state.scoring["Assumption Quality"] +
        0.25 * st.session_state.scoring["Risk Prioritization"] +
        0.25 * st.session_state.scoring["Experiment Fit"] +
        0.10 * st.session_state.scoring["Resource Efficiency"] +
        0.10 * st.session_state.scoring["Learning Outcome"]
    )

    # Build reasons
    reasons: Dict[str, str] = {}
    # 1) Risk Prioritization
    if coverage >= 0.67:
        reasons["Risk Prioritization"] = "You hit most of the top-ranked risks in Round 1—good sequencing."
    elif coverage >= 0.34:
        reasons["Risk Prioritization"] = "You addressed some top risks early; consider moving the riskiest to Round 1."
    else:
        reasons["Risk Prioritization"] = "You left top risks for later rounds—start with the hardest unknowns next time."

    # 2) Experiment Fit
    if fit_pct >= 0.85:
        reasons["Experiment Fit"] = "Your chosen tests matched assumption types well (several good-fit cards)."
    elif fit_pct >= 0.7:
        reasons["Experiment Fit"] = "Mixed fit—some tests matched, others were only loosely aligned."
    else:
        reasons["Experiment Fit"] = "Many tests weren’t ideal for the assumptions—review card descriptions to improve fit."

    # 3) Resource Efficiency
    if resource_score >= 0.8:
        reasons["Resource Efficiency"] = "Balanced spend with slight early bias and little idle budget."
    elif resource_score >= 0.6:
        reasons["Resource Efficiency"] = "Reasonable use of tokens, but consider pushing more learning into earlier rounds."
    else:
        reasons["Resource Efficiency"] = "You left significant tokens idle or saved too much for late rounds—run more scrappy tests earlier."

    # 4) Assumption Quality
    if quality >= 0.8:
        reasons["Assumption Quality"] = "Ranking looks thoughtful and your first tests targeted high-risk unknowns."
    else:
        reasons["Assumption Quality"] = "Improve the ranking step—clarify each assumption and place the scariest at the top."

    # 5) Learning Outcome
    if learning >= 0.7:
        reasons["Learning Outcome"] = "Good mix of signals and spread across assumptions."
    elif learning >= 0.45:
        reasons["Learning Outcome"] = "Some clear signals emerged; add a follow-up test where results were ambiguous."
    else:
        reasons["Learning Outcome"] = "Few actionable signals—favor tests with stronger confidence gain (e.g., pre-order, smoke test)."

    st.session_state.scoring["_reasons"] = reasons

def page_score():
    stage_header(10)
    st.subheader("Feedback & Score")
    scores = st.session_state.scoring
    if not scores:
        st.info("Run through the rounds first.")
        return

    colA, colB = st.columns(2)
    with colA:
        for k in ["Assumption Quality", "Risk Prioritization", "Experiment Fit"]:
            st.metric(k, scores[k])
    with colB:
        for k in ["Resource Efficiency", "Learning Outcome"]:
            st.metric(k, scores[k])
        st.success(f"Total Score: {scores['Total']}")

    st.markdown("### Reasons")
    for k in ["Assumption Quality", "Risk Prioritization", "Experiment Fit", "Resource Efficiency", "Learning Outcome"]:
        st.write(f"**{k}:** {scores['_reasons'][k]}")

    st.markdown("### What to do next")
    st.write("• Plan a follow-up test for any assumption with mixed/weak signals.")
    st.write("• Convert at least one successful scrappy test into a clearer metric target for your next milestone.")
    st.divider()
    if st.button("Restart Simulation"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        init_state()
        st.experimental_rerun()

# ==============================================================================
# Router
# ==============================================================================

def main():
    init_state()
    try:
        stage = st.session_state.stage
        if stage == "intro":
            page_intro()
        elif stage == "idea":
            page_choose_idea()
        elif stage == "rank":
            page_rank()
        elif stage == "r1_select":
            page_round_select("r1", 3, "r1_results")
        elif stage == "r1_results":
            page_round_results("r1", 4, "r2_select", "Round 1 — Results")
        elif stage == "r2_select":
            page_round_select("r2", 5, "r2_results")
        elif stage == "r2_results":
            page_round_results("r2", 6, "r3_select", "Round 2 — Results")
        elif stage == "r3_select":
            page_round_select("r3", 7, "r3_results")
        elif stage == "r3_results":
            page_round_results("r3", 8, "learning", "Round 3 — Results")
        elif stage == "learning":
            page_learning()
        elif stage == "score":
            page_score()
        else:
            page_intro()
    except Exception as e:
        st.error("Unexpected error. See details below.")
        st.exception(e)

if __name__ == "__main__":
    main()
