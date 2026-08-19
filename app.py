"""
AI Game Forge — a Streamlit front-end for the Multi-Agent Game Builder
LangGraph pipeline (Director -> Architect -> Engineer -> Save Code ->
Execution -> QA -> Scorer -> Human Review).

Run locally with: streamlit run app.py
"""

import os
import re
import uuid
import operator
import subprocess
from typing import TypedDict, Annotated

import streamlit as st
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv(override=True)

# Streamlit Page Config MUST be the first Streamlit command executed
st.set_page_config(
    page_title="AgentArcade",
    page_icon="🕹️",
    layout="centered",
)

# Check API Keys safely without stopping before rendering
if not os.environ.get("GROQ_API_KEY"):
    try:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
    except Exception:
        pass

if not os.environ.get("GROQ_API_KEY"):
    st.error(
        "⚠️ GROQ_API_KEY not found. "
        "Add it to your .env locally or Streamlit Cloud Secrets."
    )
    st.stop()

    
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.types import interrupt, Command
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq

if os.environ.get("LANGCHAIN_API_KEY"):
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", "dino-runner-multiagent")

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.2)

# ============================================================
# PAGE STYLING
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323:wght@400&display=swap');

    :root {
        --bg-deep: #0b0e14;
        --bg-panel: #12161f;
        --neon-green: #39ff88;
        --neon-amber: #ffb545;
        --neon-pink: #ff4d8d;
        --neon-blue: #4dd0ff;
        --grid-line: rgba(57, 255, 136, 0.06);
    }

    html, body, [class*="css"] {
        font-family: 'VT323', monospace;
        font-size: 20px;
        color: #d6f5e3;
    }
    h1, h2, h3, h4 {
        font-family: 'Press Start 2P', cursive !important;
        letter-spacing: 1px;
    }

    .stApp {
        background-color: var(--bg-deep);
        background-image:
            linear-gradient(var(--grid-line) 1px, transparent 1px),
            linear-gradient(90deg, var(--grid-line) 1px, transparent 1px);
        background-size: 28px 28px;
    }

    .creature-strip {
        display: flex;
        justify-content: center;
        gap: 2.2rem;
        font-size: 2.4rem;
        margin-bottom: 0.4rem;
        user-select: none;
    }

    .arcade-title {
        text-align: center;
        color: var(--neon-green);
        text-shadow: 0 0 10px rgba(57, 255, 136, 0.6);
        font-size: 1.9rem;
        margin-bottom: 0.2rem;
    }
    .arcade-subtitle {
        text-align: center;
        color: #8fae9e;
        font-size: 1.15rem;
        margin-bottom: 1.4rem;
    }
    .arcade-panel {
        background: var(--bg-panel);
        border: 2px solid rgba(57, 255, 136, 0.35);
        border-radius: 10px;
        padding: 1.4rem 1.5rem;
        margin-bottom: 1.1rem;
    }
    .console-log {
        background: #05070a;
        border: 1px solid rgba(57, 255, 136, 0.25);
        border-radius: 6px;
        padding: 0.8rem 1rem;
        max-height: 220px;
        overflow-y: auto;
        font-family: 'VT323', monospace;
        font-size: 1.05rem;
    }
    .console-line { margin: 0.15rem 0; }
    [data-testid="stMetricValue"] { color: #39ff88 !important; font-family: 'Press Start 2P', cursive !important; font-size: 1.3rem !important; }
    [data-testid="stMetricLabel"] { color: #8fae9e !important; }
    .stage-strip { display: flex; justify-content: space-between; margin-bottom: 1rem; }
    .stage-step { text-align: center; flex: 1; }
    .stage-icon { font-size: 1.6rem; }
    .stage-name { font-size: 0.8rem; }

    .stButton > button {
        font-family: 'Press Start 2P', cursive !important;
        font-size: 0.72rem !important;
        letter-spacing: 0.5px;
        line-height: 1.5 !important;
    }

    /* ambient floating creatures - spread across the full height with
       generous gaps between each (roughly 20vh apart) so nothing
       clusters together, kept OUT of the top ~15vh (header/title zone)
       and alternating far left/right so they read as scattered rather
       than lined up. */
    .critter {
        position: fixed;
        font-size: 2.4rem;
        opacity: 0.22;
        z-index: 1;
        pointer-events: none;
        filter: drop-shadow(0 0 8px rgba(57, 255, 136, 0.35));
    }
    .critter.c1 { top: 18vh; left: 4%;  animation: bob1 6s   ease-in-out infinite; }
    .critter.c2 { top: 30vh; right: 6%; animation: bob2 5s   ease-in-out infinite 0.6s; }
    .critter.c3 { top: 46vh; left: 6%;  animation: bob1 7s   ease-in-out infinite 0.3s; }
    .critter.c4 { top: 58vh; right: 4%; animation: bob2 6.5s ease-in-out infinite 1s; }
    .critter.c5 { top: 74vh; left: 5%;  animation: bob1 5.5s ease-in-out infinite 0.9s; }
    .critter.c6 { top: 86vh; right: 7%; animation: bob2 7.2s ease-in-out infinite 0.2s; }
    @keyframes bob1 {
        0%, 100% { transform: translateY(0) rotate(-6deg); }
        50% { transform: translateY(-16px) rotate(6deg); }
    }
    @keyframes bob2 {
        0%, 100% { transform: translateY(0) rotate(6deg); }
        50% { transform: translateY(-14px) rotate(-6deg); }
    }

    /* game console soaring across the BOTTOM third of the screen now,
       instead of cutting through the header up top. */
    .flying-console {
        position: fixed;
        left: -10%;
        top: 82vh;
        font-size: 2.2rem;
        z-index: 1;
        pointer-events: none;
        opacity: 0.28;
        animation: fly-across 17s linear infinite;
        filter: drop-shadow(0 0 8px rgba(77, 208, 255, 0.5));
    }
    @keyframes fly-across {
        0%   { left: -10%; top: 84vh; transform: rotate(-8deg); }
        50%  { left: 50%;  top: 70vh; transform: rotate(4deg); }
        100% { left: 110%; top: 86vh; transform: rotate(-8deg); }
    }
    /* launch-sequence loading animation, replaces the plain spinner */
    .launch-pad {
        position: relative;
        height: 130px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-end;
        margin: 0.6rem 0 1.2rem 0;
    }
    .ship {
        font-size: 2.6rem;
        animation: ship-bob 1s ease-in-out infinite;
        filter: drop-shadow(0 0 10px rgba(57, 255, 136, 0.6));
    }
    @keyframes ship-bob {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-6px); }
    }
    .thrust {
        font-size: 1.1rem;
        margin-top: -6px;
        animation: flicker 0.25s steps(2) infinite;
    }
    @keyframes flicker {
        0% { opacity: 1; }
        50% { opacity: 0.3; }
        100% { opacity: 1; }
    }
    .laser {
        position: absolute;
        bottom: 58px;
        font-size: 1rem;
        opacity: 0;
        animation: fire 1.4s linear infinite;
    }
    .laser.l1 { left: 44%; animation-delay: 0s; }
    .laser.l2 { left: 50%; animation-delay: 0.45s; }
    .laser.l3 { left: 56%; animation-delay: 0.9s; }
    @keyframes fire {
        0%   { bottom: 58px; opacity: 1; }
        80%  { opacity: 1; }
        100% { bottom: 130px; opacity: 0; }
    }
    .loading-text {
        text-align: center;
        color: #39ff88;
        font-family: 'Press Start 2P', cursive;
        font-size: 0.85rem;
        margin-top: 0.4rem;
    }
    .dots { animation: blink 1s steps(1) infinite; }
    @keyframes blink { 50% { opacity: 0; } }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# HELPER FUNCTIONS & STATE
# ============================================================

def get_text(message) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content)

def strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()

def generate_game_summary(user_prompt: str, code: str) -> dict:
    system_prompt = (
        "You name and summarize a game based on its build request and final source code.\n"
        "Respond in EXACTLY this format:\n"
        "TITLE: <a punchy 2-5 word game name>\n"
        "DESCRIPTION: <2-3 plain sentences on what the game is and how to play it>"
    )
    instruction = f"Original request: {user_prompt}\n\nFinal code:\n{code[:3000]}"
    try:
        response = llm.invoke([("system", system_prompt), ("human", instruction)])
        raw = get_text(response)
        title_match = re.search(r"TITLE:\s*(.+)", raw)
        desc_match = re.search(r"DESCRIPTION:\s*(.+)", raw, re.DOTALL)
        return {
            "title": title_match.group(1).strip() if title_match else "Your Game",
            "description": desc_match.group(1).strip() if desc_match else user_prompt,
        }
    except Exception:
        return {"title": "Your Game", "description": user_prompt}

try:
    import sys as _sys
    _STDLIB_MODULES = set(_sys.stdlib_module_names)
except AttributeError:
    _STDLIB_MODULES = {"os", "sys", "re", "time", "random", "math", "json", "subprocess", "typing", "collections", "datetime"}

def build_requirements_txt(code: str) -> str:
    found = set()
    for line in code.splitlines():
        line = line.strip()
        m = re.match(r"^import\s+([\w\.]+)", line) or re.match(r"^from\s+([\w\.]+)\s+import", line)
        if m:
            top_level = m.group(1).split(".")[0]
            if top_level and top_level not in _STDLIB_MODULES:
                found.add(top_level)
    found.add("pygame")
    return "\n".join(sorted(found)) + "\n"

class GameState(TypedDict):
    user_prompt: str
    director_messages: Annotated[list, add_messages]
    architect_messages: Annotated[list, add_messages]
    engineer_code: Annotated[list, add_messages]
    qa_feedback: Annotated[list, add_messages]
    current_actor: str
    iteration: int
    iteration_score: Annotated[list, operator.add]
    file_saved: bool

# ============================================================
# NODES
# ============================================================

def director_node(state: GameState):
    return {"director_messages": [HumanMessage(content=state["user_prompt"])], "current_actor": "architect"}

def architect_node(state: GameState):
    director_request = get_text(state["director_messages"][-1])
    system_prompt = "You are a software architect. Break down the 2D pygame game request into clear components."
    response = llm.invoke([("system", system_prompt), ("human", director_request)])
    return {"architect_messages": [AIMessage(content=get_text(response))], "current_actor": "engineer"}

def engineer_node(state: GameState):
    design = get_text(state["architect_messages"][-1])
    if state["qa_feedback"]:
        latest_feedback = get_text(state["qa_feedback"][-1])
        instruction = f"Fix these issues:\n{latest_feedback}\n\nCurrent code:\n{get_text(state['engineer_code'][-1])}"
    else:
        instruction = f"Write a complete Python pygame game based on this design:\n{design}"

    system_prompt = "You are a Python game developer using pygame. Return ONLY complete, runnable Python code."
    response = llm.invoke([("system", system_prompt), ("human", instruction)])
    return {
        "engineer_code": [AIMessage(content=strip_code_fences(get_text(response)))],
        "current_actor": "execution_manager",
        "iteration": state["iteration"] + 1,
    }

def save_code_node(state: GameState):
    latest_code = get_text(state["engineer_code"][-1])
    # FIX: no encoding was specified here, so Python fell back to the
    # OS default - cp1252 on Windows - which can't represent every
    # Unicode character an LLM might write (e.g. U+2011 "non-breaking
    # hyphen" instead of a plain ASCII "-" inside a comment). That's
    # exactly what raised UnicodeEncodeError. utf-8 can represent any
    # character the model could plausibly generate.
    with open("generated_game.py", "w", encoding="utf-8") as f:
        f.write(latest_code)
    return {"file_saved": True, "current_actor": "execution_manager"}

def execution_node(state: GameState):
    full_code = get_text(state["engineer_code"][-1])
    approval = interrupt({
        "question": "Approve running the generated code?",
        "code_preview": full_code,
        "line_count": full_code.count("\n") + 1,
        "char_count": len(full_code),
        "iteration": state["iteration"],
    })

    if approval != "y":
        return {"qa_feedback": [ToolMessage(content="Execution rejected.", tool_call_id="execution_manager")], "current_actor": "qa"}

    headless_env = dict(os.environ)
    headless_env["SDL_VIDEODRIVER"] = "dummy"
    headless_env["SDL_AUDIODRIVER"] = "dummy"
    # Also force UTF-8 for the subprocess's own stdio, in case the
    # generated code prints anything with non-ASCII characters (e.g.
    # emoji in a print statement) - otherwise the child process would
    # inherit the same cp1252 default and could crash on ITS OWN output.
    headless_env["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(
            ["python", "generated_game.py"],
            capture_output=True,
            text=True,
            timeout=8,
            env=headless_env,
            # FIX: subprocess.run's text=True decodes stdout/stderr using
            # the OS default encoding (cp1252 on Windows) unless told
            # otherwise. Same root cause as save_code_node above, just
            # on the read side instead of the write side.
            encoding="utf-8",
            errors="replace",
        )
        execution_log = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        execution_log = f"Process ran for 8s (expected for headless game).\nSTDOUT:\n{out}\nSTDERR:\n{err}"

    return {"qa_feedback": [ToolMessage(content=execution_log, tool_call_id="execution_manager")], "current_actor": "qa"}

def qa_node(state: GameState):
    code = get_text(state["engineer_code"][-1])
    design = get_text(state["architect_messages"][-1])
    execution_log = get_text(state["qa_feedback"][-1])

    system_prompt = "You are a QA engineer. Review code & logs against design. List concrete bugs in plain English."
    instruction = f"Design:\n{design}\n\nCode:\n{code}\n\nExecution:\n{execution_log}"
    response = llm.invoke([("system", system_prompt), ("human", instruction)])
    return {"qa_feedback": [AIMessage(content=get_text(response))], "current_actor": "scorer"}

def scorer_node(state: GameState):
    qa_report = get_text(state["qa_feedback"][-1])
    system_prompt = "Output ONLY a single integer from 1 to 10 evaluating game completeness."
    response = llm.invoke([("system", system_prompt), ("human", qa_report)])
    match = re.search(r"\d+", get_text(response).strip())
    score = int(match.group()) if match else 5
    return {"iteration_score": [max(1, min(10, score))], "current_actor": "human_review"}

def route_after_scoring(state: GameState):
    latest_score = state["iteration_score"][-1]
    decision = interrupt({
        "question": f"Current score: {latest_score}/10.",
        "options": ["loop", "finish"],
        "score": latest_score,
        "iteration": state["iteration"],
    })
    return "end" if decision == "finish" else "engineer"

# ============================================================
# GRAPH BUILD
# ============================================================

@st.cache_resource
def build_graph():
    graph = StateGraph(GameState)
    graph.add_node("director", director_node)
    graph.add_node("architect", architect_node)
    graph.add_node("engineer", engineer_node)
    graph.add_node("save_code", save_code_node)
    graph.add_node("execution", execution_node)
    graph.add_node("qa", qa_node)
    graph.add_node("scorer", scorer_node)

    graph.set_entry_point("director")
    graph.add_edge("director", "architect")
    graph.add_edge("architect", "engineer")
    graph.add_edge("engineer", "save_code")
    graph.add_edge("save_code", "execution")
    graph.add_edge("execution", "qa")
    graph.add_edge("qa", "scorer")
    graph.add_conditional_edges("scorer", route_after_scoring, {"engineer": "engineer", "end": END})

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)

app_graph = build_graph()

# ============================================================
# SESSION STATE & UI
# ============================================================

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.config = {"configurable": {"thread_id": st.session_state.thread_id}}
    st.session_state.started = False
    st.session_state.finished = False
    st.session_state.pending_interrupt = None
    st.session_state.needs_run = False
    st.session_state.event_log = []
    st.session_state.score_history = []
    st.session_state.game_input_box = ""

st.markdown('<div class="arcade-title">AGENTARCADE</div>', unsafe_allow_html=True)
st.markdown('<div class="arcade-subtitle">AI multi-agent 2D game forge</div>', unsafe_allow_html=True)

EXAMPLES = [
    ("🦖 Dino Runner", "Build me a Dino Runner game with jumping and ducking"),
    ("🐦 Flappy Bird", "Build me a Flappy Bird style game"),
    ("🐍 Snake", "Build me a Snake game with increasing speed"),
    ("👾 Space Invaders", "Build me a Space Invaders clone"),
]

def set_prompt(val):
    st.session_state.game_input_box = val

if not st.session_state.started:
    st.text_input(
        label="game_prompt",
        placeholder="e.g. Build me a Dino Runner game...",
        label_visibility="collapsed",
        key="game_input_box",
    )

    cols = st.columns(4)
    for i, (label, full_p) in enumerate(EXAMPLES):
        with cols[i]:
            st.button(label, key=f"ex_{i}", use_container_width=True, on_click=set_prompt, args=(full_p,))

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 BUILD MY GAME", type="primary", use_container_width=True):
        user_input = st.session_state.get("game_input_box", "").strip()
        if user_input:
            st.session_state.started = True
            st.session_state.needs_run = True
            st.session_state.original_prompt = user_input
            st.session_state.resume_payload = {
                "user_prompt": user_input,
                "director_messages": [],
                "architect_messages": [],
                "engineer_code": [],
                "qa_feedback": [],
                "current_actor": "director",
                "iteration": 0,
                "iteration_score": [],
                "file_saved": False,
            }
            st.rerun()
        else:
            st.warning("Type a prompt or pick a preset above!")

else:
    if st.session_state.needs_run and not st.session_state.finished:
        loading_placeholder = st.empty()
        loading_placeholder.markdown(
            """
            <div class="launch-pad">
                <div class="laser l1">💥</div>
                <div class="laser l2">💥</div>
                <div class="laser l3">💥</div>
                <div class="ship">🚀</div>
                <div class="thrust">🔥</div>
            </div>
            <p class="loading-text">AGENTS WORKING<span class="dots">...</span></p>
            """,
            unsafe_allow_html=True,
        )

        for event in app_graph.stream(st.session_state.resume_payload, config=st.session_state.config):
            st.session_state.event_log.append(event)
            if "__interrupt__" in event:
                payload = event["__interrupt__"][0].value
                st.session_state.pending_interrupt = payload
                if "score" in payload:
                    st.session_state.score_history.append(payload["score"])
                break
        else:
            st.session_state.finished = True
            st.session_state.pending_interrupt = None

        loading_placeholder.empty()
        st.session_state.needs_run = False
        st.rerun()

    # Pipeline stepper — shows which agent is active/done instead of a raw log dump
    STAGES = [
        ("director", "📝", "PLAN"),
        ("architect", "🧩", "DESIGN"),
        ("engineer", "💻", "CODE"),
        ("execution", "🧪", "TEST"),
        ("qa", "🔍", "REVIEW"),
        ("scorer", "🎯", "SCORE"),
    ]
    reached = set()
    for e in st.session_state.event_log:
        reached.update(e.keys())

    stepper_html = '<div class="stage-strip">'
    for key, icon, label in STAGES:
        color = "#39ff88" if key in reached else "#3a4048"
        stepper_html += (
            f'<div class="stage-step" style="color:{color};">'
            f'<div class="stage-icon">{icon}</div><div class="stage-name">{label}</div></div>'
        )
    stepper_html += "</div>"
    st.markdown(stepper_html, unsafe_allow_html=True)

    with st.expander("🖥️ Agent console (details)"):
        lines = []
        for e in st.session_state.event_log[-15:]:
            for k in e:
                lines.append(f'<div class="console-line">&gt; {k.upper()} done</div>')
        body = "".join(lines) if lines else '<div class="console-line">&gt; standing by...</div>'
        st.markdown(f'<div class="console-log">{body}</div>', unsafe_allow_html=True)

    # Interrupt Handling
    if st.session_state.pending_interrupt:
        payload = st.session_state.pending_interrupt
        if "code_preview" in payload:
            round_num = len(st.session_state.score_history) + 1
            st.markdown('<div class="arcade-panel">', unsafe_allow_html=True)
            st.markdown(f"<h4>🎮 ROUND {round_num} — BUILD COMPILED</h4>", unsafe_allow_html=True)
            st.write("The Engineer just finished this round's code. Fire it up?")
            with st.expander("🔍 Peek at the code first"):
                st.code(payload["code_preview"][:800] + "\n...", language="python")

            c1, c2 = st.columns([3, 1])
            with c1:
                if st.button("▶ RUN TEST", type="primary", use_container_width=True):
                    st.session_state.resume_payload = Command(resume="y")
                    st.session_state.pending_interrupt = None
                    st.session_state.needs_run = True
                    st.rerun()
            with c2:
                if st.button("⏭ Skip", use_container_width=True):
                    st.session_state.resume_payload = Command(resume="n")
                    st.session_state.pending_interrupt = None
                    st.session_state.needs_run = True
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        elif "options" in payload:
            st.markdown('<div class="arcade-panel">', unsafe_allow_html=True)
            current_score = payload.get("score", 5)
            best_score = max(st.session_state.score_history) if st.session_state.score_history else current_score
            m1, m2 = st.columns(2)
            m1.metric("THIS ROUND", f"{current_score}/10")
            m2.metric("🏆 BEST SO FAR", f"{best_score}/10")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔁 KEEP IMPROVING", type="primary", use_container_width=True):
                    st.session_state.resume_payload = Command(resume="loop")
                    st.session_state.pending_interrupt = None
                    st.session_state.needs_run = True
                    st.rerun()
            with c2:
                if st.button("🏁 FINISH & SHIP", use_container_width=True):
                    st.session_state.resume_payload = Command(resume="finish")
                    st.session_state.pending_interrupt = None
                    st.session_state.needs_run = True
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # Completion View
    if st.session_state.finished:
        st.balloons()
        st.markdown('<div class="arcade-panel">', unsafe_allow_html=True)
        st.markdown("<h2>🏆 GAME COMPLETE!</h2>", unsafe_allow_html=True)
        if st.session_state.score_history:
            st.markdown(
                f"<p style='text-align:center; color:#39ff88; font-size:1.3rem;'>"
                f"Best score achieved: {max(st.session_state.score_history)}/10 "
                f"(across {len(st.session_state.score_history)} round"
                f"{'s' if len(st.session_state.score_history) != 1 else ''})</p>",
                unsafe_allow_html=True,
            )

        final_code = ""
        if os.path.exists("generated_game.py"):
            # FIX: same missing-encoding issue on the read side - without
            # encoding="utf-8" here, Python uses the OS default (cp1252)
            # to decode the file, which can raise or mangle text if the
            # file (written correctly as utf-8 above) contains characters
            # outside cp1252's range.
            with open("generated_game.py", "r", encoding="utf-8") as f:
                final_code = f.read()

        st.download_button("💾 DOWNLOAD GAME (.PY)", data=final_code, file_name="game.py", mime="text/x-python")
        if st.button("🕹️ NEW GAME"):
            st.session_state.clear()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# AMBIENT BACKGROUND DECORATIONS
# ============================================================
# Rendered LAST, as its own markdown call, on every run regardless of
# app state. Streamlit gives each st.markdown() its own wrapper
# container - putting this first (as it originally was, right after
# page config) meant these position:fixed elements ended up trapped
# inside a near-empty, early container and got visually clipped/hidden
# behind everything rendered afterward (the title, panels, buttons).
# Rendering it last, after all real content already exists, fixes that.
# More creatures added, spread across the full height with generous
# gaps between each, and everything kept below ~15vh so nothing
# collides with the header/title zone up top.
st.markdown(
    """
    <div class="critter c1">🦖</div>
    <div class="critter c2">🐍</div>
    <div class="critter c3">👾</div>
    <div class="critter c4">🕹️</div>
    <div class="critter c5">🐦</div>
    <div class="critter c6">🍄</div>

    <div class="flying-console">🎮</div>
    """,
    unsafe_allow_html=True,
)