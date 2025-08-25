import asyncio
from browser_use import Agent, BrowserSession, BrowserProfile
from browser_use.llm import ChatOpenAI  # or your preferred LLM
from dotenv import load_dotenv

load_dotenv()

async def main():
    # Create a browser profile with the same args as your working Playwright script
    browser_profile = BrowserProfile(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox"]  # Your sandbox args
    )

    # Create a browser session with the profile
    browser_session = BrowserSession(
        browser_profile=browser_profile
    )

    # Create your agent with a basic task to go to example.com
    agent = Agent(
        task="Go to example.com and check if the page title shows up. If the title is visible, complete the task successfully.",
        llm=ChatOpenAI(model="gpt-4o-mini"),  # or your LLM
        browser_session=browser_session
    )

    # Run the agent
    result = await agent.run()
    print("Task completed!")
    print(f"Final result: {result.final_result()}")

if __name__ == "__main__":
    asyncio.run(main())