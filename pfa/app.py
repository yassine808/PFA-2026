from flask import Flask, render_template, jsonify, request, Response  # Single import line
import sqlite3
import pandas as pd
import ollama
from Chatbot import SteamChatbotSimple

app = Flask(__name__)

# ========================================
# Initialize chatbot at the top level
# ========================================
chatbot = SteamChatbotSimple()

# ========================================
# REST OF YOUR EXISTING CODE (dashboard functions, etc.)
# ========================================
def get_dashboard_data():
    conn = sqlite3.connect("steam.db")
    
    # Get chart data
    game_counts = pd.read_sql(
        "SELECT app_name, COUNT(*) as review_count FROM reviews GROUP BY app_name", conn
    )
    
    rec_counts = pd.read_sql(
        "SELECT app_name, recommended, COUNT(*) as count FROM reviews GROUP BY app_name, recommended", conn
    )
    
    # Get table data
    table_df = pd.read_sql("""
        SELECT 
            app_name,
            review,
            recommended,
            votes_helpful,
            steam_purchase,
            written_during_early_access,
            \"author.playtime_at_review\" as playtime
        FROM reviews 
        LIMIT 50
    """, conn)
    
    # Get KPIs
    kpis = get_kpis(conn)
    
    conn.close()
    
    return (
        game_counts.to_dict(orient="records"),
        rec_counts.to_dict(orient="records"),
        table_df.to_dict(orient="records"),
        kpis
    )

def get_kpis(conn):
    kpis = {}
    
    # Basic KPIs
    total_reviews = pd.read_sql("SELECT COUNT(*) FROM reviews", conn).iloc[0,0]
    kpis['totalReviews'] = int(total_reviews)
    
    # Rating and Satisfaction
    satisfaction = pd.read_sql(
        "SELECT AVG(CASE WHEN recommended=1 THEN 1.0 ELSE 0.0 END) FROM reviews", conn
    ).iloc[0,0] or 0
    kpis['satisfaction'] = round(satisfaction * 100, 0)
    kpis['avgRating'] = round(satisfaction * 5, 1)
    
    # Average Playtime (convert minutes to hours)
    avg_playtime_query = """
        SELECT AVG("author.playtime_at_review") / 60.0 
        FROM reviews 
        WHERE "author.playtime_at_review" > 0 AND "author.playtime_at_review" IS NOT NULL
    """
    avg_playtime_hours = pd.read_sql(avg_playtime_query, conn).iloc[0,0] or 0
    kpis['avgPlaytimeHours'] = round(avg_playtime_hours, 1)
    
    # Helpful Reviews Percentage
    helpful_reviews_query = """
        SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM reviews)
        FROM reviews 
        WHERE votes_helpful > 0
    """
    helpful_reviews_pct = pd.read_sql(helpful_reviews_query, conn).iloc[0,0] or 0
    kpis['helpfulReviewsPct'] = round(helpful_reviews_pct, 0)
    
    # Steam Purchase Percentage
    steam_purchase_query = """
        SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM reviews)
        FROM reviews 
        WHERE steam_purchase = 1
    """
    steam_purchase_pct = pd.read_sql(steam_purchase_query, conn).iloc[0,0] or 0
    kpis['steamPurchasePct'] = round(steam_purchase_pct, 0)
    
    # Early Access Percentage
    early_access_query = """
        SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM reviews)
        FROM reviews 
        WHERE written_during_early_access = 1
    """
    early_access_pct = pd.read_sql(early_access_query, conn).iloc[0,0] or 0
    kpis['earlyAccessPct'] = round(early_access_pct, 0)
    
    # Additional KPIs
    experienced_query = """
        SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM reviews)
        FROM reviews 
        WHERE "author.playtime_at_review" > 600
    """
    experienced_pct = pd.read_sql(experienced_query, conn).iloc[0,0] or 0
    kpis['experiencedPlayersPct'] = round(experienced_pct, 0)
    
    free_copy_query = """
        SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM reviews)
        FROM reviews 
        WHERE received_for_free = 1
    """
    free_copy_pct = pd.read_sql(free_copy_query, conn).iloc[0,0] or 0
    kpis['freeCopyPct'] = round(free_copy_pct, 0)
    
    avg_helpful_query = "SELECT AVG(votes_helpful) FROM reviews"
    avg_helpful = pd.read_sql(avg_helpful_query, conn).iloc[0,0] or 0
    kpis['avgHelpfulVotes'] = round(avg_helpful, 1)
    
    kpis['change'] = "+4.2%"
    
    return kpis

def get_game_specific_kpis(conn, game_name):
    """Get KPIs for a specific game using SQL queries for efficiency"""
    kpis = {}
    
    # Base query with WHERE clause for specific game
    base_query = f"WHERE app_name = '{game_name}'"
    
    try:
        # Total Reviews
        total_reviews_query = f"SELECT COUNT(*) FROM reviews {base_query}"
        total_reviews = pd.read_sql(total_reviews_query, conn).iloc[0,0]
        kpis['totalReviews'] = int(total_reviews)
        
        if total_reviews == 0:
            return kpis  # Return empty if no reviews for this game
        
        # Rating and Satisfaction
        satisfaction_query = f"""
            SELECT AVG(CASE WHEN recommended=1 THEN 1.0 ELSE 0.0 END) 
            FROM reviews {base_query}
        """
        satisfaction = pd.read_sql(satisfaction_query, conn).iloc[0,0] or 0
        kpis['satisfaction'] = round(satisfaction * 100, 0)
        kpis['avgRating'] = round(satisfaction * 5, 1)
        
        # Average Playtime
        avg_playtime_query = f"""
            SELECT AVG("author.playtime_at_review") / 60.0 
            FROM reviews 
            {base_query} AND "author.playtime_at_review" > 0 AND "author.playtime_at_review" IS NOT NULL
        """
        avg_playtime_hours = pd.read_sql(avg_playtime_query, conn).iloc[0,0] or 0
        kpis['avgPlaytimeHours'] = round(avg_playtime_hours, 1)
        
        # Helpful Reviews Percentage
        helpful_reviews_query = f"""
            SELECT COUNT(*) * 100.0 / {total_reviews}
            FROM reviews 
            {base_query} AND votes_helpful > 0
        """
        helpful_reviews_pct = pd.read_sql(helpful_reviews_query, conn).iloc[0,0] or 0
        kpis['helpfulReviewsPct'] = round(helpful_reviews_pct, 0)
        
        # Steam Purchase Percentage
        steam_purchase_query = f"""
            SELECT COUNT(*) * 100.0 / {total_reviews}
            FROM reviews 
            {base_query} AND steam_purchase = 1
        """
        steam_purchase_pct = pd.read_sql(steam_purchase_query, conn).iloc[0,0] or 0
        kpis['steamPurchasePct'] = round(steam_purchase_pct, 0)
        
        # Early Access Percentage
        early_access_query = f"""
            SELECT COUNT(*) * 100.0 / {total_reviews}
            FROM reviews 
            {base_query} AND written_during_early_access = 1
        """
        early_access_pct = pd.read_sql(early_access_query, conn).iloc[0,0] or 0
        kpis['earlyAccessPct'] = round(early_access_pct, 0)
        
        # Additional KPIs
        experienced_query = f"""
            SELECT COUNT(*) * 100.0 / {total_reviews}
            FROM reviews 
            {base_query} AND "author.playtime_at_review" > 600
        """
        experienced_pct = pd.read_sql(experienced_query, conn).iloc[0,0] or 0
        kpis['experiencedPlayersPct'] = round(experienced_pct, 0)
        
        free_copy_query = f"""
            SELECT COUNT(*) * 100.0 / {total_reviews}
            FROM reviews 
            {base_query} AND received_for_free = 1
        """
        free_copy_pct = pd.read_sql(free_copy_query, conn).iloc[0,0] or 0
        kpis['freeCopyPct'] = round(free_copy_pct, 0)
        
        avg_helpful_query = f"SELECT AVG(votes_helpful) FROM reviews {base_query}"
        avg_helpful = pd.read_sql(avg_helpful_query, conn).iloc[0,0] or 0
        kpis['avgHelpfulVotes'] = round(avg_helpful, 1)
        
        kpis['change'] = "+4.2%"
        
    except Exception as e:
        print(f"Error calculating KPIs for {game_name}: {e}")
        # Return empty KPIs on error
    
    return kpis

@app.route("/api/kpis/<game_name>")
def get_game_kpis(game_name):
    conn = sqlite3.connect("steam.db")
    
    try:
        if game_name == "all":
            # Use the existing get_kpis function for all games
            kpis = get_kpis(conn)
        else:
            # Use the new efficient function for specific game
            kpis = get_game_specific_kpis(conn, game_name)
        
        conn.close()
        
        # Ensure all required KPI keys exist
        required_kpis = ['avgRating', 'satisfaction', 'totalReviews', 'change', 
                        'avgPlaytimeHours', 'helpfulReviewsPct', 'steamPurchasePct', 
                        'earlyAccessPct', 'experiencedPlayersPct', 'freeCopyPct', 
                        'avgHelpfulVotes']
        
        for kpi in required_kpis:
            if kpi not in kpis:
                kpis[kpi] = '--'
        
        return jsonify(kpis)
        
    except Exception as e:
        print(f"Error in get_game_kpis: {e}")
        conn.close()
        return jsonify({}), 500

@app.route("/")
def dashboard():
    try:
        bar_data, stack_data, table_data, kpis = get_dashboard_data()
        
        # Ensure all KPI keys exist
        required_kpis = ['avgRating', 'satisfaction', 'totalReviews', 'change', 
                        'avgPlaytimeHours', 'helpfulReviewsPct', 'steamPurchasePct', 
                        'earlyAccessPct', 'experiencedPlayersPct', 'freeCopyPct', 
                        'avgHelpfulVotes']
        
        for kpi in required_kpis:
            if kpi not in kpis:
                kpis[kpi] = '--'
        
        return render_template(
            "dashboard.html",
            bar_data=bar_data,
            stack_data=stack_data,
            table_data=table_data,
            kpis=kpis
        )
    except Exception as e:
        print(f"Error in dashboard: {e}")
        # Return empty data on error
        return render_template(
            "dashboard.html",
            bar_data=[],
            stack_data=[],
            table_data=[],
            kpis={}
        )

@app.route("/reviews")
def reviews():
    try:
        conn = sqlite3.connect("steam.db")
        
        # Get unique games with their app_id
        games_df = pd.read_sql("""
            SELECT DISTINCT 
                app_id,
                app_name,
                COUNT(*) as review_count,
                AVG(CASE WHEN recommended=1 THEN 1.0 ELSE 0.0 END) as satisfaction_rate
            FROM reviews 
            GROUP BY app_id, app_name
            ORDER BY app_name
        """, conn)
        
        conn.close()
        
        games_list = games_df.to_dict(orient="records")
        
        return render_template(
            "reviews.html",
            games=games_list
        )
    except Exception as e:
        print(f"Error in reviews page: {e}")
        return render_template(
            "reviews.html",
            games=[]
        )

# KEEP THIS ONE - it's the correct route for your game reviews page
@app.route("/game_reviews/<game_name>")
def game_reviews_page(game_name):
    try:
        conn = sqlite3.connect("steam.db")
        
        # Get reviews for specific game, sorted by helpful votes (high to low)
        reviews_df = pd.read_sql("""
            SELECT 
                app_id,
                app_name,
                review,
                recommended,
                votes_helpful,
                votes_funny,
                steam_purchase,
                written_during_early_access,
                \"author.playtime_at_review\" as playtime
            FROM reviews 
            WHERE app_name = ?
            ORDER BY votes_helpful DESC
            LIMIT 50
        """, conn, params=(game_name,))
        
        conn.close()
        
        reviews_list = reviews_df.to_dict(orient="records")
        
        # Get app_id from first review if available
        app_id = None
        if reviews_list and reviews_list[0].get('app_id'):
            app_id = reviews_list[0]['app_id']
        
        return render_template(
            "game_reviews.html",
            game_name=game_name,
            reviews=reviews_list,
            total_reviews=len(reviews_list),
            app_id=app_id  # Pass app_id to template
        )
    except Exception as e:
        print(f"Error in game reviews page: {e}")
        return render_template(
            "game_reviews.html",
            game_name=game_name,
            reviews=[],
            total_reviews=0,
            app_id=None
        )

#========================================chatbot============================================

@app.route("/chatbot")
def chatbot_page():
    """Render the chatbot page"""
    try:
        return render_template("chatbot.html")
    except Exception as e:
        print(f"Error loading chatbot page: {e}")
        return "Error loading chatbot page", 500

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        
        if not user_message:
            return jsonify({"error": "Empty message"}), 400
        
        # Get response from chatbot
        response = chatbot.get_answer(user_message)
        
        return jsonify({
            "response": response,
            "success": True
        })
        
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({"error": "Failed to process request", "success": False}), 500

# FIXED: Add streaming endpoint - request is accessed OUTSIDE the generator
@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    try:
        # Get the request data OUTSIDE the generator
        data = request.get_json()
        user_message = data.get("message", "").strip()
        
        if not user_message:
            def error_stream():
                yield "data: Sorry, I didn't receive your message.\n\n"
                yield "data: [DONE]\n\n"
            return Response(error_stream(), mimetype="text/event-stream")
        
        def generate():
            try:
                # Stream response from chatbot
                for token in chatbot.get_answer_stream(user_message):
                    yield f"data: {token}\n\n"
                
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                print(f"Stream chat error: {e}")
                yield f"data: Sorry, I encountered an error: {str(e)}\n\n"
                yield "data: [DONE]\n\n"
        
        return Response(generate(), mimetype="text/event-stream")
        
    except Exception as e:
        print(f"Stream endpoint error: {e}")
        def error_stream():
            yield f"data: Sorry, I encountered an error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"
        return Response(error_stream(), mimetype="text/event-stream")

# Update the game_info endpoint
@app.route("/api/game_info", methods=["GET"])
def get_game_info():
    """Get information about games for the chatbot to reference"""
    try:
        game_info = chatbot.get_game_info(limit=10)
        
        return jsonify({
            "games": game_info,
            "success": True
        })
        
    except Exception as e:
        print(f"Game info error: {e}")
        return jsonify({"games": [], "success": False})

# Add clear history endpoint
@app.route("/api/chat/clear", methods=["POST"])
def clear_chat_history():
    """Clear chat history"""
    try:
        chatbot.clear_history()
        return jsonify({"success": True, "message": "Chat history cleared"})
    except Exception as e:
        print(f"Clear history error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)