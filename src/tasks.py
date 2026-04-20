from crewai import Task

def create_tasks(goal: str, architect, researcher, coder, debugger, qa, reviewer, scribe):

    plan_task = Task(
        description=(
            f"Analyze the following user goal and write a detailed architecture and implementation plan.\n"
            f"Goal: {goal}\n\n"
            f"Write the full plan directly in your response as a structured markdown document. "
            f"Include: project overview, file structure, technology choices, and step-by-step implementation guide. "
            f"Do NOT use any tools. Just write the plan as your response text."
        ),
        expected_output="A comprehensive markdown-formatted implementation plan covering architecture, file structure, and step-by-step guide.",
        agent=architect
    )

    research_task = Task(
        description=(
            f"Review the project goal: {goal}\n\n"
            f"Based on your knowledge, list the best libraries, patterns, and approaches to implement this. "
            f"You do NOT need to call any tools. Just provide a clear written summary of your recommendations."
        ),
        expected_output="A concise written list of technical recommendations and best practices.",
        agent=researcher
    )

    code_task = Task(
        description=(
            f"Implement the full codebase for: {goal}\n\n"
            f"DESIGN REQUIREMENTS (MUST FOLLOW):\n"
            f"- Use a Premium, Modern Aesthetic: Vibrant colors, smooth gradients, and clean layouts.\n"
            f"- Responsive: Must look perfect on both mobile (375px) and desktop.\n"
            f"- Typography: Use Google Fonts (e.g., 'Inter', 'Roboto', or 'Press Start 2P' for retro).\n"
            f"- Polish: Add hover effects, subtle shadows, and interactive feedback for buttons.\n"
            f"- Code Structure: Keep HTML, CSS, and JS in separate files for clean organization.\n\n"
            f"Use the 'Write File Tool' to write each file. "
            f"For example, to write index.html: call 'Write File Tool' with filepath='index.html' and content=<full html code>.\n"
            f"Write ALL necessary files. After writing, use 'Execute Command Tool' to check for syntax errors only (do NOT start servers).\n"
            f"ONLY use: 'Write File Tool' and 'Execute Command Tool'."
        ),
        expected_output="A stunning, fully functional, and responsive codebase saved in the project workspace.",
        agent=coder,
        context=[plan_task, research_task]
    )

    debug_task = Task(
        description=(
            f"Review the Coder's work. If there are bugs or errors:\n"
            f"1. Use 'Read File Tool' with filepath=<filename> to read the broken file.\n"
            f"2. Use 'Write File Tool' with filepath=<filename> and fixed content to save the fix.\n"
            f"3. Use 'Execute Command Tool' to run the code and confirm it works.\n"
            f"Only use these tools: 'Read File Tool', 'Write File Tool', 'Execute Command Tool'."
        ),
        expected_output="A verified, bug-free codebase with all files saved in the workspace.",
        agent=debugger,
        context=[code_task]
    )

    qa_task = Task(
        description=(
            f"Test the completed application.\n"
            f"Use 'Execute Command Tool' to run available tests or the main application file.\n"
            f"Use 'Read File Tool' to inspect code files if needed.\n"
            f"Write a short QA summary report as plain text output (no file needed).\n"
            f"Only use: 'Execute Command Tool' and 'Read File Tool'."
        ),
        expected_output="A written QA report confirming the application works or listing any remaining issues.",
        agent=qa,
        context=[debug_task]
    )

    review_task = Task(
        description=(
            f"Perform a final code review of the project.\n"
            f"Use 'Read File Tool' to read each source file.\n"
            f"Then use 'Write File Tool' with filepath='review.md' to save your review findings.\n"
            f"Only use: 'Read File Tool' and 'Write File Tool'."
        ),
        expected_output="A review.md file saved in the workspace summarizing code quality findings.",
        agent=reviewer,
        context=[qa_task]
    )

    scribe_task = Task(
        description=(
            f"Generate a comprehensive README.md for the project.\n"
            f"Use 'Read File Tool' to read the plan.md and review.md if available.\n"
            f"Then use 'Write File Tool' with filepath='README.md' to save the final documentation.\n"
            f"The README must include: project description, setup instructions, usage guide, and file structure.\n"
            f"Only use: 'Read File Tool' and 'Write File Tool'."
        ),
        expected_output="A complete README.md file saved in the workspace.",
        agent=scribe,
        context=[review_task]
    )

    return [plan_task, research_task, code_task, debug_task, qa_task, review_task, scribe_task]
