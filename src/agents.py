from crewai import Agent
from .tools import execute_command_tool, write_file_tool, read_file_tool

def create_architect(llm=None) -> Agent:
    return Agent(
        role='Architect',
        goal='Design the project structure and create a detailed actionable plan.',
        backstory="You are a seasoned software architect. You break down complex goals into modular, easy-to-implement steps. You output your plan as a detailed `plan.md`.",
        verbose=True,
        allow_delegation=False,
        tools=[write_file_tool],
        llm=llm
    )

def create_researcher(llm=None) -> Agent:
    return Agent(
        role='Researcher',
        goal='Gather up-to-date information on best practices, APIs, and libraries required for the project.',
        backstory="You are an expert technical researcher. You find the best tools and documentation to help the engineering team succeed.",
        verbose=True,
        allow_delegation=False,
        tools=[], # Add search tools if needed in the future
        llm=llm
    )

def create_coder(llm=None) -> Agent:
    return Agent(
        role='Principal Engineer',
        goal='Implement the project based on the Architect plan, writing code and executing it in the sandbox to verify it works.',
        backstory="You are a 10x developer. You write clean, efficient, and well-documented code. You test your code by running it in your sandbox environment. ALWAYS write a requirements.txt if needed. ALWAYS verify the code using the execute_command_tool.",
        verbose=True,
        allow_delegation=False,
        tools=[write_file_tool, read_file_tool, execute_command_tool],
        llm=llm
    )

def create_debugger(llm=None) -> Agent:
    return Agent(
        role='Code Surgeon (Debugger)',
        goal='Analyze execution errors from the Principal Engineer and surgically fix the broken code.',
        backstory="You are an expert at debugging complex errors. You don't rewrite entire files; you carefully analyze tracebacks, identify the exact line of failure, and apply precise fixes. You run the code again to verify your fixes.",
        verbose=True,
        allow_delegation=False,
        tools=[write_file_tool, read_file_tool, execute_command_tool],
        llm=llm
    )

def create_reviewer(llm=None) -> Agent:
    return Agent(
        role='Gatekeeper (Code Reviewer)',
        goal='Review the final codebase for style, security, and performance, and write a final review.md document.',
        backstory="You are a strict but fair principal engineer who gates all releases. You ensure the code adheres to best practices and doesn't contain glaring security flaws. You output a `review.md`.",
        verbose=True,
        allow_delegation=False,
        tools=[read_file_tool, write_file_tool],
        llm=llm
    )

def create_qa(llm=None) -> Agent:
    return Agent(
        role='Guardian (QA Engineer)',
        goal='Ruthlessly test the application to ensure it works flawlessly. Attempt to break it and report any failures.',
        backstory="You are a meticulous Quality Assurance engineer. You use the execute_command_tool to run the application or tests. If it fails, you report exactly what failed so it can be fixed. You do not write code, you only test.",
        verbose=True,
        allow_delegation=False,
        tools=[execute_command_tool, read_file_tool],
        llm=llm
    )

def create_scribe(llm=None) -> Agent:
    return Agent(
        role='Scribe (Technical Writer)',
        goal='Analyze the final codebase and generate a comprehensive README.md and documentation.',
        backstory="You are a world-class technical writer. You take complex code and explain it beautifully in markdown. You output a `README.md` containing setup instructions, architecture overview, and usage guide.",
        verbose=True,
        allow_delegation=False,
        tools=[read_file_tool, write_file_tool],
        llm=llm
    )
