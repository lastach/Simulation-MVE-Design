# Simulation #2 — Designing & Running Early Experiments (ThermaLoop)
# -------------------------------------------------------------------
# Learners identify key risks, run scrappy experiments, and get feedback.

import random
import pandas as pd
import streamlit as st

# --- Optional drag-and-drop component -----------------------------------------
try:
    from streamlit_dnd_list import dnd_list
except Exception:
    dnd_list = None

FORCE_NO_DND = False  # set to True if Streamlit Cloud still fails to load dnd_list
if FORCE_NO_DND:
    dnd_list = None

# ------------------------------------------------------------------------------
st.set_page_config(page_title="Simulation #2 — ThermaLoop", page_icon="🧪", layout="wide")
st.title("Simulation #2 — Designing & Running Early Experiments")
st.caption("ThermaLoop: rank risks, pick scrappy tests, learn quickly")

# ------------------------------------------------------------------------------
# Initialize session state
if "stage" not in st.session_state:
    st.session_state.stage = "intro"
    st.session_state.idea_key = None
    st.session_state.rank_ids = []
    st.session_state.tokens = {"r1": 8, "r2": 8, "r3": 6}
    st.session_state.portfolio = {"r1": [], "r2": [], "r3": []}
    st.session_state.results = {"r1": [], "r2": [], "r3": []}
    st.session_state.scoring = {}

S = st.session_state

# ------------------------------------------------------------------------------
IDEA_CARDS = {
    "homeowners": {
        "title": "Homeowner: Comfort & Energy",
        "assumptions": [
            "Homeowners will try a 14-day free trial.",
            "Main motivation is saving money, not comfort.",
            "Self-install can be done in <45 minutes.",
            "Users will allow data collection from thermostat.",
            "Monthly price under $9 is acceptable.",
            "Comfort improvement visible within 7 days.",
            "Mobile notifications drive weekly action.",
            "Family members won’t object to auto-schedule.",
        ],
    },
    "landlords": {
        "title": "Small Landlords: Portfolio Savings",
        "assumptions": [
            "Landlords will share thermostat data for each unit.",
            "Premium $49/month tier is viable.",
            "Main value is fewer maintenance visits.",
            "80 % activation within 2 weeks possible.",
            "Tenants won’t disable automations.",
            "Property-manager partners can drive warm leads.",
        ],
    },
    "installers": {
        "title": "HVAC Installers: Smart Upsell",
        "assumptions": [
            "Installers accept a 20 % revenue share.",
            "Techs can demo app in < 5 min on site.",
            "Customers approve data collection at install time.",
            "Comfort-focused pitch converts best.",
            "CRM integration can wait until later.",
        ],
    },
}

EXPERIMENTS = [
    ("Landing Page Test", 3, "Create a simple page and send traffic to see who clicks / signs up."),
    ("Smoke Test", 3, "Offer a ‘Reserve Now’ / ‘Join Waitlist’ to test intent pre-product."),
    ("Concierge Trial", 4, "Manually deliver the value to a few users and observe outcomes."),
    ("Wizard-of-Oz Prototype", 4, "Fake the backend while showing a real UI to gauge reactions."),
    ("Pre-Order Test", 4, "Ask for card details or deposits to measure true willingness to pay."),
    ("Ad Split Test", 3, "Run small ads with different messages to see what draws attention."),
    ("Expert Interview", 2, "Quick calls with domain experts to surface feasibility / policy blockers."),
]

ROUND_BUDGET = {"r1": 8, "r2": 8, "r3": 6}

# ------------------------------------------------------------------------------
def header(stage):
    tabs = ["Intro", "Choose Idea", "Rank Risks",
            "Round 1", "Round 2", "Round 3", "Learning", "Score"]
    cols = st.columns(len(tabs))
    for i, name in enumerate(tabs):
        with cols[i]:
            if i == stage:
                st.button(f"✅ {name}", disabled=True)
            else:
                st.button(name, key=f"tab{i}")


def goto(stage_name):
    S.stage = stage_name
    st.experimental_rerun()

# ------------------------------------------------------------------------------
def page_intro():
    header(0)
    st.markdown("""
**Objective:** Identify your riskiest assumptions and run fast, low-cost tests.

**Flow:**
1. Choose your idea focus  
2. Rank assumptions from most → least risky  
3. Use tokens to run experiments across 3 rounds  
4. Review learning and receive coaching feedback
""")
    if st.button("Start"):
        goto("idea")

# ------------------------------------------------------------------------------
def page_idea():
    header(1)
    st.subheader("Choose your idea focus")
    cols = st.columns(len(IDEA_CARDS))
    for i, (k, card) in enumerate(IDEA_CARDS.items()):
        with cols[i]:
            st.markdown(f"**{card['title']}**")
            if st.button("Select", key=f"select_{k}"):
                S.idea_key = k
                S.rank_ids = list(range(len(card["assumptions"])))
                goto("rank")
    if S.idea_key:
        st.markdown("Preview assumptions:")
        for a in IDEA_CARDS[S.idea_key]["assumptions"]:
            st.write("-", a)

# ------------------------------------------------------------------------------
def page_rank():
    header(2)
    st.subheader("Rank assumptions (highest → lowest risk)")

    assumptions = IDEA_CARDS[S.idea_key]["assumptions"]
    if dnd_list is not None:
        items = [f"{i+1}. {txt}" for i, txt in enumerate(assumptions)]
        reordered = dnd_list(items, direction="vertical", draggable=True)
        if reordered:
            new_order = [assumptions[int(r.split('.')[0]) - 1] for r in reordered]
            S.rank_ids = [assumptions.index(a) for a in new_order]
    else:
        st.info("Drag-and-drop unavailable — enter numeric ranks below.")
        ranks = {}
        for i, a in enumerate(assumptions):
            ranks[i] = st.number_input(a, 1, len(assumptions), i+1, key=f"r{i}")
        S.rank_ids = [k for k, _ in sorted(ranks.items(), key=lambda kv: kv[1])]

    if st.button("Proceed to Round 1"):
        goto("r1")

# ------------------------------------------------------------------------------
def run_round(round_key):
    results = []
    for aid, exp in S.portfolio[round_key]:
        success = random.random() > 0.4
        detail = random.choice([
            "Strong positive signal",
            "Moderate interest but low conversion",
            "Mixed feedback – needs follow-up",
            "Weak signal – assumption invalidated"
        ])
        results.append({"Assumption": exp[0], "Experiment": exp[1],
                        "Success": success, "Detail": detail})
    S.results[round_key] = results

# ------------------------------------------------------------------------------
def select_round(round_key, next_stage):
    header({"r1":3,"r2":4,"r3":5}[round_key])
    st.subheader(f"{round_key.upper()} – Select Experiments")
    tokens = S.tokens[round_key]
    st.write(f"Tokens remaining: **{tokens}**")
    assumptions = [IDEA_CARDS[S.idea_key]["assumptions"][i] for i in S.rank_ids]

    for a in assumptions:
        with st.expander(a):
            for name, cost, desc in EXPERIMENTS:
                disabled = cost > S.tokens[round_key]
                if st.button(f"Run {name} ({cost})", disabled=disabled, key=f"{round_key}_{a}_{name}"):
                    if cost <= S.tokens[round_key]:
                        S.tokens[round_key] -= cost
                        S.portfolio[round_key].append((a, (a, name)))
                        st.success(f"Added {name} for '{a}'  ({S.tokens[round_key]} tokens left)")
    if st.button("Run Selected Tests"):
        run_round(round_key)
        goto(next_stage)

# ------------------------------------------------------------------------------
def show_results(round_key, next_stage):
    header({"r1":3,"r2":4,"r3":5}[round_key])
    st.subheader(f"{round_key.upper()} – Results")
    if not S.results[round_key]:
        st.info("No tests yet.")
    else:
        st.dataframe(pd.DataFrame(S.results[round_key]), hide_index=True)
    if st.button("Next Round" if round_key!="r3" else "Learning Summary"):
        goto(next_stage)

# ------------------------------------------------------------------------------
def page_learning():
    header(6)
    st.subheader("Learning Summary")
    all_res = S.results["r1"] + S.results["r2"] + S.results["r3"]
    if not all_res:
        st.info("No data yet.")
    else:
        df = pd.DataFrame(all_res)
        st.dataframe(df, hide_index=True)
    if st.button("View Feedback & Score"):
        calc_score()
        goto("score")

# ------------------------------------------------------------------------------
def calc_score():
    total_tests = sum(len(S.results[k]) for k in ["r1","r2","r3"])
    variety = len({r["Assumption"] for res in S.results.values() for r in res})
    S.scoring = {
        "Assumption Coverage": min(100, 50 + variety*10),
        "Experiment Volume": min(100, 40 + total_tests*8),
        "Resource Use": max(60, 100 - sum(S.tokens.values())*5),
    }
    S.scoring["Total"] = int(
        (S.scoring["Assumption Coverage"] +
         S.scoring["Experiment Volume"] +
         S.scoring["Resource Use"]) / 3
    )

# ------------------------------------------------------------------------------
def page_score():
    header(7)
    st.subheader("Feedback & Score")
    if not S.scoring:
        st.info("Run the simulation first.")
        return
    for k, v in S.scoring.items():
        if k != "Total":
            st.metric(k, v)
    st.success(f"Total Score: {S.scoring['Total']}")
    st.markdown("### Coaching Notes")
    if S.scoring["Assumption Coverage"] < 80:
        st.write("→ Focus earlier tests on the riskiest assumptions.")
    if S.scoring["Experiment Volume"] < 80:
        st.write("→ Use remaining tokens each round to maximize learning.")
    if S.scoring["Resource Use"] < 80:
        st.write("→ Balance effort and signal by favoring scrappy tests.")
    st.divider()
    if st.button("Restart Simulation"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.experimental_rerun()

# ------------------------------------------------------------------------------
# Router
def main():
    try:
        if S.stage == "intro": page_intro()
        elif S.stage == "idea": page_idea()
        elif S.stage == "rank": page_rank()
        elif S.stage == "r1": select_round("r1", "r1_results")
        elif S.stage == "r1_results": show_results("r1", "r2")
        elif S.stage == "r2": select_round("r2", "r2_results")
        elif S.stage == "r2_results": show_results("r2", "r3")
        elif S.stage == "r3": select_round("r3", "r3_results")
        elif S.stage == "r3_results": show_results("r3", "learning")
        elif S.stage == "learning": page_learning()
        elif S.stage == "score": page_score()
    except Exception as e:
        st.error("Unexpected error in Simulation #2")
        st.exception(e)

if __name__ == "__main__":
    main()
