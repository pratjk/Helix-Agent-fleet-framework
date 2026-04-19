import os
from dotenv import load_dotenv
from crewai import Crew, Process

from src.agents import create_architect, create_researcher, create_coder, create_debugger, create_reviewer
from src.tasks import create_tasks

# Load environment variables
load_dotenv()

def run_helix_fleet(goal: str):
    print("\n🚀 Initializing Helix Agent Fleet...\n")
    
    llm = os.getenv("MODEL", "gpt-4o-mini")
    print(f"Using Model: {llm}")
    
    architect = create_architect(llm=llm)
    researcher = create_researcher(llm=llm)
    coder = create_coder(llm=llm)
    debugger = create_debugger(llm=llm)
    reviewer = create_reviewer(llm=llm)
    
    tasks = create_tasks(goal, architect, researcher, coder, debugger, reviewer)
    
    crew = Crew(
        agents=[architect, researcher, coder, debugger, reviewer],
        tasks=tasks,
        verbose=True,
        process=Process.sequential,
        memory=True
    )
    
    print("\n🚀 Starting Mission...\n")
    result = crew.kickoff()
    
    print("\n==============================================")
    print("MISSION ACCOMPLISHED")
    print("==============================================")
    print("Final result from the crew:")
    print(result)
    print("\nCheck the 'workspace' directory for the generated files.")

if __name__ == "__main__":
    print("==============================================")
    print("        Welcome to Project Helix CLI!         ")
    print("==============================================")
    print("Ensure you have Docker Desktop running to use the sandbox.")
    print("Ensure your .env file is configured with the correct API keys for your chosen provider.\n")
    
    print("Supported Model Formats (via LiteLLM):")
    print("  - OpenAI: gpt-4o")
    print("  - Anthropic: claude-3-5-sonnet-20240620")
    print("  - DeepSeek: deepseek/deepseek-chat")
    print("  - Qwen: qwen/qwen-max")
    print("  - OpenRouter: openrouter/qwen/qwen-plus (Use any model!)")
    print("  - Local Ollama: ollama/llama3\n")
    print("You can type the exact LiteLLM provider string, or use a simple alias like 'deepseek'.")
    
    user_model = input("Enter your desired model (press enter to default to gpt-4o-mini): ").strip().lower()
    
    # Map simple names to LiteLLM formatted names
    model_aliases = {
        "openai": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-20240620",
        "deepseek": "deepseek/deepseek-chat",
        "qwen": "qwen/qwen-max",
        "groq": "groq/llama3-8b-8192",
        "ollama": "ollama/llama3"
    }
    
    if user_model in model_aliases:
        user_model = model_aliases[user_model]

    if user_model:
        os.environ["MODEL"] = user_model
    else:
        os.environ["MODEL"] = "gpt-4o-mini"

    user_goal = input("\nWhat do you want to build? ")
    if user_goal.strip():
        run_helix_fleet(user_goal)
    else:
        print("No goal provided. Exiting.")
