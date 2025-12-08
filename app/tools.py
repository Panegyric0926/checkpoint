"""
Tools module for the agent
Contains internet search tool using Tavily API
"""
from langchain_tavily import TavilySearch
from app.config import config
import os

# Set Tavily API key in environment
os.environ["TAVILY_API_KEY"] = config.TAVILY_API_KEY


def get_search_tool():
    """Get the Tavily search tool for internet searches"""
    search = TavilySearch(
        max_results=5,
        topic="general",
        include_answer=True,
        include_raw_content=False,
    )
    return search


def get_tools():
    """Get all tools available to the agent"""
    return [get_search_tool()]
