#!/usr/bin/env python3
"""
Main Application Entry Point
AI Chat Agent with Time Travel (Checkpoint) Feature

Features:
- LangGraph-based agent system
- Internet search capability via Tavily
- Checkpoint mechanism for conversation time-travel
- Langfuse integration for prompt management and tracing
- Dash-based web frontend
"""

from app.config import config
from app.dash_app import create_app


def validate_config() -> bool:
    """Validate configuration before starting"""
    errors = config.validate()
    if errors:
        print("Configuration errors found:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease update your .env file with the required values.")
        return False
    return True


def main():
    """Main entry point"""
    print("=" * 60)
    print("  AI Chat Agent with Time Travel")
    print("  Powered by LangGraph")
    print("=" * 60)
    print()
    
    # Validate configuration
    if not validate_config():
        print("\nStarting anyway for demo purposes...")
        print("Note: Some features may not work without proper configuration.\n")
    
    # Create and run the Dash app
    app = create_app()
    
    print(f"Starting server at http://{config.APP_HOST}:{config.APP_PORT}")
    print("Press Ctrl+C to stop the server\n")
    
    app.run(
        host=config.APP_HOST,
        port=config.APP_PORT,
        debug=config.DEBUG
    )


if __name__ == "__main__":
    main()
