from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.tools import tool
from typing import List
import requests
import os
import base64
import json
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

@CrewBase
class NewsAutomation():
    """NewsAutomation crew"""

    agents: List[BaseAgent]
    tasks: List[Task]
    
    @tool("NewsFetcherTool")
    def NewsFetcherTool(topic: str) -> dict:
        """
        Searches for the latest news and developments related to the given topic.
        Returns concise, relevant, and up-to-date information suitable for news summaries.
        """
        url = "https://google.serper.dev/search"

        payload = {
          "q": topic
        }
        headers = {
          'X-API-KEY': os.environ.get("SERPER_API_KEY"),
          'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, json=payload)

        return response.json()

    @tool("SlackBotTool")
    def SlackBotTool(summaries: list, channel: str = "#general") -> dict:
        """
        Sends summaries to Slack using Incoming Webhook.
        Input: summaries (list of dicts)
        Each dict should contain:
          - headline
          - summary
          - url
        """
    
        webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
        if not webhook_url:
            raise Exception("Missing SLACK_WEBHOOK_URL in environment variables")
    
        blocks = []
        for item in summaries:
            blocks.extend([
                {"type": "section", "text": {"type": "mrkdwn",
                    "text": f"*<{item['url']}|{item['headline']}>*\n{item['summary']}"
                }},
                {"type": "divider"}
            ])
    
        payload = {
            "channel": channel,
            "blocks": blocks
        }
    
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
    
        return {"status": "sent", "count": len(summaries)} 
    
    @tool("GoogleSheetsLogger")
    def GoogleSheetsLogger(news_items: list) -> dict:
        """
        news_items = [
            {"date": "...", "headline": "...", "summary": "...", "url": "..."},
            ...
        ]
        """

        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        info = json.loads(base64.b64decode(os.environ["GCP_CREDENTIALS_B64"]).decode("utf-8"))
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)

        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()

        SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
        RANGE = "Sheet1!A:D"

        rows = []
        for item in news_items:
            rows.append([item["date"], item["headline"], item["summary"], item["url"]])

        body = {"values": rows}
        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE,
            valueInputOption="RAW",
            body=body
        ).execute()

        return {"status": "logged", "rows_added": result.get("updates").get("updatedRows")}

    @agent
    def news_fetcher(self) -> Agent:
        return Agent(
            config=self.agents_config['news_fetcher'], # type: ignore[index]
            tools=[self.NewsFetcherTool],
            verbose=True
        )
    
    @agent
    def news_summarizer(self) -> Agent:
        return Agent(
            config=self.agents_config['news_summarizer'], # type: ignore[index]
            verbose=True
        )
    
    @agent
    def slack_bot(self) -> Agent:
        return Agent(
            config=self.agents_config['slack_bot'],
            tools=[self.SlackBotTool],
            verbose=True
        )
    
    @agent
    def google_sheets_logger(self) -> Agent:
        return Agent(
            config=self.agents_config['google_sheets_logger'],
            tools=[self.GoogleSheetsLogger],
            verbose=True
        )
    
    @task
    def newsfetch_task(self) -> Task:
        return Task(
            config=self.tasks_config['newsfetch_task'], # type: ignore[index]
        )
    
    @task
    def news_summary_task(self) -> Task:
        return Task(
            config=self.tasks_config['news_summary_task'], # type: ignore[index]
        )
    
    @task
    def slack_task(self) -> Task:
        return Task(
            config=self.tasks_config['slack_task'],
        )
    
    @task
    def google_sheets_task(self) -> Task:
        return Task(
            config=self.tasks_config['google_sheets_task'],
        )
    
    @crew
    def crew(self) -> Crew:
        """Creates the NewsAutomation crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
