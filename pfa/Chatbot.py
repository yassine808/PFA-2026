# -*- coding: utf-8 -*-

import sqlite3
import pandas as pd
import ollama
from datetime import datetime

class SteamChatbotSimple:
    def __init__(self, db_path="steam.db"):
        """
        Simple Steam Chatbot without vector store dependencies
        """
        self.db_path = db_path
        self.chat_history = []
        
    def get_game_summary(self):
        """
        Get summary statistics about games in the database
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get game statistics
            games_query = """
                SELECT 
                    COUNT(DISTINCT app_name) as total_games,
                    COUNT(*) as total_reviews,
                    AVG(CASE WHEN recommended=1 THEN 1.0 ELSE 0.0 END) * 100 as avg_satisfaction,
                    AVG("author.playtime_at_review") / 60.0 as avg_playtime_hours
                FROM reviews
            """
            stats_df = pd.read_sql(games_query, conn)
            
            # Get top games
            top_games_query = """
                SELECT 
                    app_name,
                    COUNT(*) as review_count,
                    AVG(CASE WHEN recommended=1 THEN 1.0 ELSE 0.0 END) * 100 as satisfaction_rate
                FROM reviews 
                GROUP BY app_name
                ORDER BY review_count DESC
                LIMIT 10
            """
            top_games_df = pd.read_sql(top_games_query, conn)
            
            conn.close()
            
            summary = {
                "total_games": int(stats_df.iloc[0]['total_games']),
                "total_reviews": int(stats_df.iloc[0]['total_reviews']),
                "avg_satisfaction": round(stats_df.iloc[0]['avg_satisfaction'], 1),
                "avg_playtime_hours": round(stats_df.iloc[0]['avg_playtime_hours'], 1),
                "top_games": top_games_df.to_dict('records')
            }
            
            return summary
            
        except Exception as e:
            print(f"Error getting game summary: {e}")
            return None
    
    def get_game_info(self, game_name=None, limit=5):
        """
        Get information about specific games or all games
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            if game_name:
                # Get specific game info
                query = """
                    SELECT 
                        app_name,
                        COUNT(*) as review_count,
                        AVG(CASE WHEN recommended=1 THEN 1.0 ELSE 0.0 END) * 100 as satisfaction_rate,
                        AVG("author.playtime_at_review") / 60.0 as avg_playtime_hours,
                        AVG(votes_helpful) as avg_helpful_votes
                    FROM reviews 
                    WHERE app_name LIKE ?
                    GROUP BY app_name
                """
                games_df = pd.read_sql(query, conn, params=(f"%{game_name}%",))
            else:
                # Get all games info
                query = """
                    SELECT 
                        app_name,
                        COUNT(*) as review_count,
                        AVG(CASE WHEN recommended=1 THEN 1.0 ELSE 0.0 END) * 100 as satisfaction_rate,
                        AVG("author.playtime_at_review") / 60.0 as avg_playtime_hours
                    FROM reviews 
                    GROUP BY app_name
                    ORDER BY review_count DESC
                    LIMIT ?
                """
                games_df = pd.read_sql(query, conn, params=(limit,))
            
            conn.close()
            
            games_info = []
            for _, game in games_df.iterrows():
                games_info.append({
                    "name": game['app_name'],
                    "review_count": int(game['review_count']),
                    "satisfaction_rate": round(game['satisfaction_rate'], 1),
                    "avg_playtime_hours": round(game['avg_playtime_hours'], 1) if pd.notna(game['avg_playtime_hours']) else 0,
                    "avg_helpful_votes": round(game.get('avg_helpful_votes', 0), 1) if 'avg_helpful_votes' in game else 0
                })
            
            return games_info
            
        except Exception as e:
            print(f"Error getting game info: {e}")
            return []
    
    def format_context_for_llm(self, question):
        """
        Format database information as context for the LLM
        Returns a clear warning if no data is found
        """
        context_parts = []
        
        # Get game summary
        summary = self.get_game_summary()
        if summary:
            context_parts.append(f"""
DATABASE SUMMARY:
- Total Games: {summary['total_games']:,}
- Total Reviews: {summary['total_reviews']:,}
- Average Satisfaction: {summary['avg_satisfaction']}%
- Average Playtime: {summary['avg_playtime_hours']:.1f} hours

TOP 10 GAMES BY REVIEW COUNT:
""")
            
            # Add top games
            for i, game in enumerate(summary['top_games'][:10], 1):
                context_parts.append(f"{i}. {game['app_name']}: {game['review_count']:,} reviews ({game['satisfaction_rate']:.1f}% satisfaction)")
        
        # Look for specific game names in the question
        games_info = []
        
        # Try to extract game names (simple pattern matching)
        words = question.lower().split()
        potential_game_names = [word.capitalize() for word in words if len(word) > 3]
        
        for game_name in potential_game_names[:3]:  # Limit to 3 games
            game_data = self.get_game_info(game_name, limit=1)
            if game_data:
                games_info.extend(game_data)
        
        # If no specific games found, check for general queries
        if not games_info and any(keyword in question.lower() for keyword in ["top", "popular", "best", "worst", "highest", "lowest"]):
            games_info = self.get_game_info(limit=5)
        
        # Add games info to context
        if games_info:
            context_parts.append("\nSPECIFIC GAME INFORMATION:")
            for game in games_info[:5]:  # Limit to 5 games
                context_parts.append(f"""
- {game['name']}:
  * Reviews: {game['review_count']:,}
  * Satisfaction: {game['satisfaction_rate']}%
  * Avg Playtime: {game['avg_playtime_hours']:.1f} hours
  * Avg Helpful Votes: {game['avg_helpful_votes']:.1f}
""")
        
        # If no context was found at all
        if not context_parts:
            return "DATABASE IS EMPTY OR NO INFORMATION FOUND. Only say: 'I don't have any data in my database.'"
        
        return "\n".join(context_parts)
    
    def get_answer(self, question: str):
        """
        Get answer for a question using Ollama - ONLY using database information
        """
        try:
            # Format context from database
            context = self.format_context_for_llm(question)
            
            # Create messages for Ollama
            messages = [
                {
                    "role": "system",
                    "content": f"""You are a Steam gaming assistant. You MUST follow these rules STRICTLY:

CRITICAL RULES:
1. ONLY use the database information provided below
2. NEVER use any external knowledge or make up information
3. If the database doesn't have information about something, say: "I don't have information about that in my database"
4. Only analyze and report on what's in the database
5. Do not speculate or assume anything
6. Do not use any knowledge beyond what's in the database below

DATABASE INFORMATION YOU CAN USE:
{context}

FORMATTING GUIDELINES:
1. Format numbers with commas: 9,635,437 not 9635437
2. Use proper spacing in numbered lists: "1. " not "1."
3. Put each numbered item on a new line
4. Use markdown: **bold** for emphasis
5. Use bullet points for lists
6. Always cite the data: "According to my database..."

RESPONSE EXAMPLES:
Good: "Based on my database, Stellaris has 542,322 reviews with 87.2% satisfaction."
Bad: "I think Stellaris is popular because..." (speculation)
Good: "I don't have information about that specific game in my database."
Bad: "I'm not sure, but maybe..." (making things up)

Current date: {datetime.now().strftime('%Y-%m-%d')}
"""
                }
            ]
            
            # Add chat history (last 3 messages)
            for msg in self.chat_history[-6:]:  # Keep last 3 exchanges
                messages.append(msg)
            
            # Add current question
            messages.append({"role": "user", "content": question})
            
            # Call Ollama with stricter settings
            response = ollama.chat(
                model="gemma3:4b",  # Use your model
                messages=messages,
                options={
                    "temperature": 0.3,  # Lower temperature for more factual responses
                    "top_p": 0.8,
                    "num_predict": 512
                }
            )
            
            answer = response['message']['content']
            
            # Update chat history
            self.chat_history.append({"role": "user", "content": question})
            self.chat_history.append({"role": "assistant", "content": answer})
            
            # Keep history manageable
            if len(self.chat_history) > 20:
                self.chat_history = self.chat_history[-20:]
            
            return answer
            
        except Exception as e:
            print(f"Error getting answer: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    def get_answer_stream(self, question: str):
        """
        Stream answer for a question - ONLY using database information
        """
        try:
            # Format context from database
            context = self.format_context_for_llm(question)
            
            # Create messages for Ollama
            messages = [
                {
                    "role": "system",
                    "content": f"""You are a Steam gaming assistant. You MUST follow these rules STRICTLY:

CRITICAL RULES:
1. ONLY use the database information provided below
2. NEVER use any external knowledge or make up information
3. If the database doesn't have information about something, say: "I don't have information about that in my database"
4. Only analyze and report on what's in the database
5. Do not speculate or assume anything
6. Do not use any knowledge beyond what's in the database below

DATABASE INFORMATION YOU CAN USE:
{context}

FORMATTING GUIDELINES:
1. Format numbers with commas: 9,635,437 not 9635437
2. Use proper spacing in numbered lists: "1. " not "1."
3. Put each numbered item on a new line
4. Use markdown: **bold** for emphasis
5. Use bullet points for lists
6. Always cite the data: "According to my database..."

RESPONSE EXAMPLES:
Good: "Based on my database, Stellaris has 542,322 reviews with 87.2% satisfaction."
Bad: "I think Stellaris is popular because..." (speculation)
Good: "I don't have information about that specific game in my database."
Bad: "I'm not sure, but maybe..." (making things up)

Current date: {datetime.now().strftime('%Y-%m-%d')}
"""
                }
            ]
            
            # Add chat history
            for msg in self.chat_history[-6:]:
                messages.append(msg)
            
            # Add current question
            messages.append({"role": "user", "content": question})
            
            # Stream response from Ollama
            stream = ollama.chat(
                model="gemma3:4b",  # Use your model
                messages=messages,
                stream=True,
                options={
                    "temperature": 0.3,  # Lower temperature for more factual responses
                    "top_p": 0.8,
                    "num_predict": 512
                }
            )
            
            full_response = ""
            for chunk in stream:
                if chunk['message']['content']:
                    token = chunk['message']['content']
                    full_response += token
                    yield token
            
            # Update chat history
            self.chat_history.append({"role": "user", "content": question})
            self.chat_history.append({"role": "assistant", "content": full_response})
            
            if len(self.chat_history) > 20:
                self.chat_history = self.chat_history[-20:]
                
        except Exception as e:
            print(f"Error streaming answer: {e}")
            yield f"Sorry, I encountered an error: {str(e)}"
    
    def clear_history(self):
        """Clear chat history"""
        self.chat_history = []
    
    def chat_loop(self):
        """
        Simple command-line chat interface for testing
        """
        print("\n" + "="*50)
        print("Steam Gaming Assistant (Simple Version)")
        print("="*50)
        print("Type 'quit' to exit, 'clear' to clear history, 'summary' for statistics\n")
        
        while True:
            try:
                question = input("\nYou: ").strip()
                
                if question.lower() == 'quit':
                    print("Goodbye!")
                    break
                elif question.lower() == 'clear':
                    self.clear_history()
                    print("Chat history cleared!")
                    continue
                elif question.lower() == 'summary':
                    summary = self.get_game_summary()
                    if summary:
                        print(f"\n📊 Game Database Summary:")
                        print(f"Total Games: {summary['total_games']:,}")
                        print(f"Total Reviews: {summary['total_reviews']:,}")
                        print(f"Average Satisfaction: {summary['avg_satisfaction']}%")
                        print(f"Average Playtime: {summary['avg_playtime_hours']:.1f} hours")
                        print(f"\nTop Games:")
                        for game in summary['top_games'][:5]:
                            print(f"- {game['app_name']}: {game['review_count']:,} reviews ({game['satisfaction_rate']:.1f}% satisfaction)")
                    continue
                
                if not question:
                    continue
                
                print("\nAssistant: ", end="", flush=True)
                
                # Stream the response
                response = ""
                for token in self.get_answer_stream(question):
                    print(token, end="", flush=True)
                    response += token
                print()
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")

# Main execution for testing
if __name__ == "__main__":
    # Create chatbot instance
    chatbot = SteamChatbotSimple()
    
    # Run chat loop
    chatbot.chat_loop()