import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from google.generativeai.types.safety_types import HarmBlockThreshold, HarmCategory
from crewai import Crew, Process, Agent, Task
from helper import TavilySearchTool, setup_logging
import textwrap

# Setup logging
logger = setup_logging()

def initialize_llm():
    """Initialize and return Google Generative AI chat model with specified configuration"""
    try:
        load_dotenv()
        llm = ChatGoogleGenerativeAI(
            model='gemini-1.5-flash',
            verbose=True,
            temperature=0.75,
            top_p=0.6, 
            top_k=45,
            timeout=300,
            max_output_tokens=2500,
            max_retries=2,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            safety_settings = {
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        return llm
    except Exception as e:
        logger.error(f"Error occurred in initialize_llm: {str(e)}")

# Initialize LLM
llm = initialize_llm()

# Create search agent
search_agent = Agent(
    role = 'internet search agent',
    goal = textwrap.dedent("""Search the web for information about: {topic}"""),
    backstory = textwrap.dedent("""I am a research agent that searches the web to find relevant information."""),
    tools = [TavilySearchTool.search_internet],
    llm = llm,
    verbose = True,
    memory = True,
    max_iter = 5,
)

# Create search task
search_task = Task(
    description = textwrap.dedent("""Search the web for: {topic}\nFind relevant information and summarize the key findings
                                  and must add top 5 links from where you got the findings."""),
    expected_output = textwrap.dedent("""A clear summary along with of search results with relevant source links."""),
    agent = search_agent,
)

# Create search crew
search_crew = Crew(
    agents = [search_agent],
    tasks = [search_task], 
    process = Process.sequential,
    share_crew = False,
    cache = True,
    verbose = True,
    output_log_file = "logs/search_crew.log",
)
