import pandas as pd

def get_dashboard_data():
    df = pd.read_csv("dataset/steam_eng_20games.csv")

    # Reviews per game
    game_counts = df['app_name'].value_counts().reset_index()
    game_counts.columns = ['app_name', 'review_count']

    # Recommended vs Not Recommended per game
    rec_counts = df.groupby(['app_name','recommended']).size().reset_index(name='count')

    # Sample 3 reviews per game (if needed)
    table_df = df.groupby('app_name').head(3)

    # Convert data to dicts for JS
    bar_data = game_counts.to_dict(orient="records")
    stack_data = rec_counts.to_dict(orient="records")
    table_data = table_df.to_dict(orient="records")

    return bar_data, stack_data, table_data
