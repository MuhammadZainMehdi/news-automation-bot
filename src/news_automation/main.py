#!/usr/bin/env python
import sys
import warnings

from datetime import datetime

from .crew import NewsAutomation

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def run():
    """
    Run the crew.
    """
    print("CrewAI started!")

    inputs = {
        'topic': 'Artificial Intelligence and Tech',
        'current_year': str(datetime.now().year)
    }

    try:
        NewsAutomation().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")