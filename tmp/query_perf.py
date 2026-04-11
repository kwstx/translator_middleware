import sqlite3
import pandas as pd

def query_db():
    conn = sqlite3.connect('engram.db')
    query = """
    SELECT 
        tool_registry.name as tool, 
        backend_selected as backend, 
        AVG(latency_ms) as avg_latency, 
        AVG(success) as success_rate, 
        AVG(token_cost_actual) as avg_token_cost, 
        COUNT(*) as samples 
    FROM tool_registry 
    JOIN tool_routing_decision ON tool_registry.id = tool_routing_decision.tool_id 
    GROUP BY tool, backend;
    """
    df = pd.read_sql_query(query, conn)
    print(df.to_markdown())
    conn.close()

if __name__ == "__main__":
    query_db()
