from crewai import Task

def create_tasks(goal: str, architect, researcher, coder, debugger, qa, reviewer, scribe):
    plan_task = Task(
        description=f"Analyze the following user goal and create a detailed architecture and implementation plan. Goal: {goal}. Save the plan to 'plan.md' in the workspace using the write_file_tool.",
        expected_output="A detailed plan.md file saved in the workspace.",
        agent=architect
    )

    research_task = Task(
        description=f"Review the goal: {goal}. Research best practices, potential pitfalls, and specific libraries or patterns that should be used. Provide a summary to the Coder.",
        expected_output="A list of technical recommendations and best practices for the implementation.",
        agent=researcher
    )

    code_task = Task(
        description="Implement the codebase according to the Architect's plan. Use the workspace tools to write files (e.g., main.py, requirements.txt). Run the code in the sandbox to verify it works, and fix any errors you encounter.",
        expected_output="A fully functioning codebase saved in the workspace, tested and verified via the sandbox.",
        agent=coder,
        context=[plan_task, research_task]
    )

    debug_task = Task(
        description="Review the output from the Coder. If there are any execution errors or incomplete features, use your tools to analyze the code, find the bug, and apply surgical fixes. Run the code again to verify your fixes.",
        expected_output="A bug-free, fully functional codebase.",
        agent=debugger,
        context=[code_task]
    )

    qa_task = Task(
        description="Run the completed application or write automated tests to verify functionality. Attempt to break the application and report any failures.",
        expected_output="A QA report indicating the application runs flawlessly or detailing any persistent issues.",
        agent=qa,
        context=[debug_task]
    )

    review_task = Task(
        description="Perform a final code review of the workspace. Check for clean code practices, security flaws, and ensure the original goal was met. Generate a 'review.md' document summarizing your findings.",
        expected_output="A 'review.md' file saved in the workspace containing the final code review.",
        agent=reviewer,
        context=[qa_task]
    )

    scribe_task = Task(
        description="Analyze the final codebase, review report, and QA report. Generate a comprehensive and beautifully formatted README.md file in the workspace explaining how to set up and run the application.",
        expected_output="A complete README.md file saved in the workspace.",
        agent=scribe,
        context=[review_task]
    )

    return [plan_task, research_task, code_task, debug_task, qa_task, review_task, scribe_task]
