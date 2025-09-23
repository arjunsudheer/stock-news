from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from typing import Dict, Any, Sequence
from datetime import datetime
import json


class StockAnalysisSystem:
    def __init__(self):
        debator_client = OllamaChatCompletionClient(
            model="mistral-nemo",
            model_info={
                "vision": False,
                "function_calling": True,
                "json_output": False,
                "family": "mistral",
                "structured_output": False,
                "multiple_system_messages": False,
            },
        )
        moderation_client = OllamaChatCompletionClient(
            model="llama-guard3:latest",
            model_info={
                "vision": False,
                "function_calling": False,
                "json_output": False,
                "family": "llama-3.3-8b",
                "structured_output": False,
                "multiple_system_messages": False,
            },
        )

        buy_agent = AssistantAgent(
            name="BuyAgent",
            description="This agent argues in favor of buying the stock.",
            model_client=debator_client,
            system_message="""You are an optimistic stock market analyst who believes in long-term growth and potential.
            Your job is to convince the other analysts on why a particular stock may be a good buy. Focus on:
            - Future market potential and growth opportunities
            - Innovative aspects of companies
            - Long-term market trends
            - Positive industry developments
            Always look for the upside potential in stock investments.
            You may reference and critique the other analysts' perspectives.""",
        )

        sell_agent = AssistantAgent(
            name="SellAgent",
            description="This agent argues in favor of selling the stock.",
            model_client=debator_client,
            system_message="""You are a cautious and skeptical stock market analyst.
            Your job is to convince the other analysts on why a particular stock may be a good sell. Focus on:
            - Current financial metrics and performance
            - Risk factors and market threats
            - Historical patterns of failure
            - Related stocks in the same sector
            - Competition and market challenges
            - Potential alternative investments that are better given the money that could be made by selling this stock
            Always consider what could go wrong with an investment.
            You may reference and critique the other analysts' perspectives.""",
        )

        hold_agent = AssistantAgent(
            name="HoldAgent",
            description="This agent argues in favor of holding the stock.",
            model_client=debator_client,
            system_message="""You are a calm and collected analyst who isn't easily swayed by emotions.
            Your job is to convince the other analysts on why a particular stock may be a good hold. Focus on:
            - Long-term potential of the stock
            - Market stability and trends
            - Balanced view of risks and rewards
            - Technical analysis indicators
            Always advocate for patience and careful consideration.
            You may reference and critique the other analysts' perspectives.""",
        )

        self.debate_facilitator_agent = AssistantAgent(
            "DebateFacilitator",
            model_client=debator_client,
            system_message="""You are a debate facilitator. Your job is to guide the discussion and ensure all perspectives are heard.

            Make sure that each analyst gets an equal opportunity to present their views. These are the analysts participating in the debate:
            - BuyAgent: Argues in favor of buying the stock.
            - SellAgent: Argues in favor of selling the stock.
            - HoldAgent: Argues in favor of holding the stock.

            For the first question, ask each analyst to provide their initial stance on the stock (buy, sell, hold) and their key reasons.
            As each analyst speaks, summarize their main points and ask clarifying questions if needed. Make sure that each agent always references
            information they found in the stock data provided or from their own research. Ask clarifying questions if any points are unclear.
            Please also challenge the perspectives on an analyst if they seem to be making unsupported claims.

            After each analyst has presented their views, facilitate a discussion where they can respond to each other's points. Make sure to 
            give a summary of what the other analysts have said before asking each agent to respond. Encourage them to debate the merits of each perspective.

            Finally, guide the group towards a consensus recommendation. Ask each analyst to summarize their final stance and reasoning.
            Ensure that all the analysts agree on one final recommendation.

            After the analysts have reached a consensus, provide a concise summary of the entire discussion, highlighting the key points from each analyst.
            Your summary must follow this exact format:

            Consensus Recommendation: [Buy/Sell/Hold]
            [Key Point 1 from BuyAgent]
            [Key Point 1 from SellAgent]
            [Key Point 1 from HoldAgent]
            [2 - 3 sentence summary of the overall discussion and why the consensus was reached.]

            End your markdown summary with 'TERMINATE' on a new line.""",
        )

        self.moderator_agent = AssistantAgent(
            name="Moderator",
            model_client=moderation_client,
        )

        # Define termination condition
        text_termination = TextMentionTermination("TERMINATE")

        # Use SelectorGroupChat to ensure ordered turn-taking between agents
        self.stock_recommendation_team = SelectorGroupChat(
            participants=[
                self.debate_facilitator_agent,
                buy_agent,
                sell_agent,
                hold_agent,
            ],
            model_client=debator_client,
            selector_prompt="""Select an agent to perform task.
            {roles}

            Current conversation context:
            {history}

            Read the above conversation, then select an agent from {participants} to perform the next task.
            Make sure the debate facilitator agent has assigned tasks before other agents start working.
            Only select one agent.
            """,
            selector_func=self.__selector_func,
            allow_repeated_speaker=True,
            termination_condition=text_termination,
            max_turns=20,
        )

    def __selector_func(
        self, messages: Sequence[BaseAgentEvent | BaseChatMessage]
    ) -> str | None:
        """
        __selector_func always provides handoff back to debate facilitator if it was not the last speaker, otherwise lets selector group chat moderator decide next handoff.

        Args:
            messages (Sequence[BaseAgentEvent  |  BaseChatMessage]): The message history of the conversation.

        Returns:
            str | None: The name of the agent to hand off to, or None if no specific handoff is needed.
        """
        if messages[-1].source != self.debate_facilitator_agent.name:
            return self.debate_facilitator_agent.name
        return None

    async def __verify_content_safety(self, content: str) -> bool:
        """
        Use llama-guard to verify content safety
        """
        # Initialize a conversation with llama-guard

        # Ask llama-guard to verify the content
        response = await self.moderator_agent.run(task=content)

        # Ignore S6 unsafe classification since stock advice is inherently risky, decreases false positives
        return response.messages[-1].content in ["safe", "unsafe\nS6"]

    async def analyze_stock(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct a full analysis of a stock using all agents
        """

        # Initial prompt with stock data
        task = f"""
        Please analyze this stock based on the following data:
        
        Symbol: {stock_data.get('stock_data', {}).get('symbol', 'Unknown')}
        Current Price: ${stock_data.get('stock_data', {}).get('current_price', 'Unknown')}
        
        Recent News:
        {json.dumps(stock_data.get('news_articles', []), indent=2)}
        
        Market Data:
        {json.dumps(stock_data.get('stock_data', {}), indent=2)}
        
        Each agent should provide their perspective on whether to buy, sell, or hold this stock.
        Consider all available information and justify your recommendations.
        """

        try:
            # Run the RoundRobinGroupChat and capture all messages
            stock_recommendations = await self.stock_recommendation_team.run(task=task)

            final_message = stock_recommendations.messages[-1].content
            final_message = final_message.replace("TERMINATE", "").strip()

            # Verify content safety - this will pause execution until moderation is complete
            is_safe = await self.__verify_content_safety(final_message)

            if not is_safe:
                final_message = "The content generated was flagged as unsafe by the moderation system."

            return {
                "recommendation": final_message,
                "full_discussion": stock_recommendations.messages,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"Error during analysis: {str(e)}")
            return {
                "recommendation": "There was an error during analysis.",
                "full_discussion": "There was an error during analysis.",
                "timestamp": datetime.now().isoformat(),
            }
