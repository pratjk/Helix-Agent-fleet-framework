import os
from crewai import Agent
from .tools import execute_command_tool, write_file_tool, read_file_tool, get_tavily_tool

# Token & safety limits to prevent runaway loops on small models
AGENT_CONFIG = {
    "max_iter": 5,
    "max_rpm": 10,
}

def resolve_model(llm: str = None) -> str:
    """
    Resolves the final model string to use.
    - If llm is provided, use it.
    - Falls back to MODEL_NAME env var.
    - Falls back to Groq (free, fast, tool-ready) if GROQ_API_KEY is set.
    - Final fallback: openrouter default.
    """
    if llm:
        return llm
    if os.getenv("MODEL_NAME"):
        return os.getenv("MODEL_NAME")
    if os.getenv("GROQ_API_KEY"):
        return "groq/llama-3.1-8b-instant"
    return "openrouter/qwen/qwen-2.5-coder-32b-instruct"

def create_architect(llm=None) -> Agent:
    model = resolve_model(llm)
    return Agent(
        role='Architect',
        goal='Design the project structure and create a detailed implementation plan.',
        backstory="You are a seasoned software architect. You break down complex goals into modular, easy-to-implement steps. You output your plan as a detailed markdown document in your response text. Do NOT use any tools.",
        verbose=True,
        allow_delegation=False,
        tools=[],  # No tools needed - plan is returned as text context
        llm=model,
        **AGENT_CONFIG
    )

def create_researcher(llm=None) -> Agent:
    model = resolve_model(llm)
    # Use Tavily for real web search if key is available
    tavily = get_tavily_tool()
    tools = [tavily] if tavily else []
    backstory = (
        "You are an expert technical researcher with web search access. "
        "You find the best tools, libraries, and documentation for the team."
        if tavily else
        "You are an expert technical researcher. Based on your knowledge, "
        "you recommend the best libraries and best practices for the project. Do NOT use any tools."
    )
    return Agent(
        role='Researcher',
        goal='Gather best practices, APIs, and library recommendations for the project.',
        backstory=backstory,
        verbose=True,
        allow_delegation=False,
        tools=tools,
        llm=model,
        **AGENT_CONFIG
    )

def create_coder(llm=None) -> Agent:
    model = resolve_model(llm)
    return Agent(
        role='Principal Engineer',
        goal='Implement the project based on the Architect plan, writing code and verifying it works.',
        backstory="You are a 10x developer. You write clean, efficient, well-documented code. ALWAYS write a requirements.txt if needed. ALWAYS verify code using execute_command_tool.",
        verbose=True,
        allow_delegation=False,
        tools=[write_file_tool, read_file_tool, execute_command_tool],
        llm=model,
        **AGENT_CONFIG
    )

def create_debugger(llm=None) -> Agent:
    model = resolve_model(llm)
    return Agent(
        role='Code Surgeon (Debugger)',
        goal='Analyze execution errors and surgically fix the broken code.',
        backstory="You are an expert debugger. You analyze tracebacks, identify the exact line of failure, apply precise fixes, and run the code again to verify.",
        verbose=True,
        allow_delegation=False,
        tools=[write_file_tool, read_file_tool, execute_command_tool],
        llm=model,
        **AGENT_CONFIG
    )

def create_reviewer(llm=None) -> Agent:
    model = resolve_model(llm)
    return Agent(
        role='Gatekeeper (Code Reviewer)',
        goal='Review the final codebase for style, security, and performance. Write a review.md.',
        backstory="You are a strict but fair principal engineer. You ensure code follows best practices and has no security flaws. You output a `review.md`.",
        verbose=True,
        allow_delegation=False,
        tools=[read_file_tool, write_file_tool],
        llm=model,
        **AGENT_CONFIG
    )

def create_qa(llm=None) -> Agent:
    model = resolve_model(llm)
    return Agent(
        role='Guardian (QA Engineer)',
        goal='Ruthlessly test the application to ensure it works. Attempt to break it and report failures.',
        backstory="You are a meticulous QA engineer. You use execute_command_tool to run tests. You do not write code — you only test and report.",
        verbose=True,
        allow_delegation=False,
        tools=[execute_command_tool, read_file_tool],
        llm=model,
        **AGENT_CONFIG
    )

def create_scribe(llm=None) -> Agent:
    model = resolve_model(llm)
    return Agent(
        role='Scribe (Technical Writer)',
        goal='Analyze the final codebase and generate a comprehensive README.md.',
        backstory="You are a world-class technical writer. You explain complex code beautifully in markdown, with setup instructions, architecture overview, and usage guide.",
        verbose=True,
        allow_delegation=False,
        tools=[read_file_tool, write_file_tool],
        llm=model,
        **AGENT_CONFIG
    )
