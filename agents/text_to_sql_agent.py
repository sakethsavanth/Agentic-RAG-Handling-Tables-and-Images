"""
Agent 5: Text-to-SQL Agent
This agent determines if a query requires SQL execution, converts natural language 
to SQL queries, and executes them against the relational database tables
"""
import os
import sys
from pathlib import Path
import re
from typing import List, Dict, Any, Optional, Tuple
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils import DatabaseManager, AWSBedrockClient
from utils.mcp_client import SQLMCPClient

# Load environment variables
load_dotenv()


class TextToSQLState(TypedDict):
    """State for Text-to-SQL workflow"""
    query: str
    requires_sql: bool
    sql_queries: List[str]
    sql_results: List[Dict[str, Any]]
    combined_result: str
    error: str
    reasoning: str


class TextToSQLAgent:
    """
    Agent 5: Text-to-SQL Agent
    Classifies queries, generates SQL, and executes against structured tables
    """
    
    def __init__(self):
        """Initialize the Text-to-SQL Agent"""
        print("\n" + "=" * 80)
        print("🤖 INITIALIZING AGENT 5: TEXT-TO-SQL AGENT")
        print("=" * 80 + "\n")
        
        self.db_manager = DatabaseManager()
        self.aws_client = AWSBedrockClient()
        self.mcp_client = SQLMCPClient()
        
        # Initialize database connection
        if self.db_manager.connect():
            print("✅ Database connection established")
        
        # Connect to MCP server
        if self.mcp_client.connect():
            print("✅ MCP server connected")
        else:
            print("⚠️ MCP server connection failed, using direct database connection")
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
        
        print("✅ Text-to-SQL Agent initialized successfully!\n")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for Text-to-SQL"""
        workflow = StateGraph(TextToSQLState)
        
        # Add nodes
        workflow.add_node("classify_query", self.classify_query)
        workflow.add_node("generate_sql", self.generate_sql)
        workflow.add_node("execute_sql", self.execute_sql)
        workflow.add_node("format_results", self.format_results)
        
        # Define edges with conditional routing
        workflow.set_entry_point("classify_query")
        workflow.add_conditional_edges(
            "classify_query",
            self._should_generate_sql,
            {
                "generate_sql": "generate_sql",
                "skip": END
            }
        )
        workflow.add_edge("generate_sql", "execute_sql")
        workflow.add_edge("execute_sql", "format_results")
        workflow.add_edge("format_results", END)
        
        return workflow.compile()
    
    def _should_generate_sql(self, state: TextToSQLState) -> str:
        """Determine if SQL generation is needed"""
        if state.get('requires_sql', False):
            return "generate_sql"
        return "skip"
    
    def classify_query(self, state: TextToSQLState) -> TextToSQLState:
        """Classify if the query requires SQL execution"""
        print("\n" + "-" * 80)
        print("🔍 STEP 1: CLASSIFYING QUERY")
        print("-" * 80)
        
        query = state.get('query', '')
        
        if not query:
            print("⚠️ No query provided\n")
            state['requires_sql'] = False
            return state
        
        print(f"📝 Query: {query[:200]}{'...' if len(query) > 200 else ''}\n")
        
        # Get available tables via MCP
        try:
            if self.mcp_client.is_connected():
                mcp_result = self.mcp_client.list_tables()
                
                if mcp_result.get('success'):
                    tables = mcp_result.get('tables', [])
                    table_info = "\n".join([
                        f"- {table['table_name']}: {table.get('description', 'No description')}"
                        for table in tables
                    ])
                    print(f"📊 Found {len(tables)} table(s) via MCP")
                else:
                    print("⚠️ MCP list_tables failed, using direct query")
                    # Fallback to direct query
                    self.db_manager.cursor.execute("""
                        SELECT DISTINCT table_name, metadata
                        FROM table_chunks
                        ORDER BY table_name;
                    """)
                    
                    tables = self.db_manager.cursor.fetchall()
                    table_info = "\n".join([
                        f"- {row['table_name']}: {row['metadata'].get('description', 'No description') if row['metadata'] else 'No description'}"
                        for row in tables
                    ])
            else:
                # Direct database query as fallback
                print("⚠️ MCP not connected, using direct database query")
                self.db_manager.cursor.execute("""
                    SELECT DISTINCT table_name, metadata
                    FROM table_chunks
                    ORDER BY table_name;
                """)
                
                tables = self.db_manager.cursor.fetchall()
                table_info = "\n".join([
                    f"- {row['table_name']}: {row['metadata'].get('description', 'No description') if row['metadata'] else 'No description'}"
                    for row in tables
                ])
            
            if not tables:
                print("⚠️ No tables available in database\n")
                state['requires_sql'] = False
                state['reasoning'] = "No tables available in database"
                return state
            
        except Exception as e:
            print(f"❌ Error fetching table list: {str(e)}\n")
            state['requires_sql'] = False
            state['error'] = str(e)
            return state
        
        # Use LLM to classify the query
        classification_prompt = f"""You are a query classifier. Analyze the user's question and determine if it requires querying structured database tables.

Available Tables:
{table_info}

User Question: {query}

Analyze the question and determine:
1. Does this question ask for specific data values, statistics, or comparisons that would be in database tables?
2. Does it mention specific entities (countries, products, scores, etc.) that would be stored in tables?
3. Or is it asking for conceptual explanations, definitions, or general knowledge?

Examples of SQL-Required Queries:
- "What is the pillar score for Indonesia?"
- "Compare the scores between Turkey and Mali"
- "Show me all countries with pillar_i_score above 70"
- "What is the average pillar II score?"

Examples of Non-SQL Queries:
- "Explain the role of business readiness"
- "What are governance factors?"
- "Describe the methodology used"

Respond in this exact format:
REQUIRES_SQL: [YES/NO]
REASONING: [Brief explanation of why SQL is or isn't needed]
EXTRACTED_PARTS: [If the question has multiple parts, list which parts need SQL]"""

        try:
            # Call LLM for classification
            result = self.aws_client.get_nova_response(
                prompt=classification_prompt,
                model_id="us.amazon.nova-pro-v1:0"
            )
            
            if result['success']:
                response_text = result['response']
                print(f"🤖 LLM Classification:\n{response_text}\n")
                
                # Parse response
                requires_sql = "REQUIRES_SQL: YES" in response_text.upper()
                
                # Extract reasoning
                reasoning_match = re.search(r'REASONING:\s*(.+?)(?:\n|$)', response_text, re.IGNORECASE | re.DOTALL)
                reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided"
                
                state['requires_sql'] = requires_sql
                state['reasoning'] = reasoning
                
                if requires_sql:
                    print("✅ Query REQUIRES SQL execution\n")
                else:
                    print("✅ Query does NOT require SQL execution\n")
            else:
                print(f"❌ Classification failed: {result.get('error', 'Unknown error')}\n")
                state['requires_sql'] = False
                state['error'] = result.get('error', 'Classification failed')
                
        except Exception as e:
            print(f"❌ Error during classification: {str(e)}\n")
            state['requires_sql'] = False
            state['error'] = str(e)
        
        return state
    
    def generate_sql(self, state: TextToSQLState) -> TextToSQLState:
        """Generate SQL query from natural language"""
        print("\n" + "-" * 80)
        print("💾 STEP 2: GENERATING SQL QUERY")
        print("-" * 80)
        
        query = state.get('query', '')
        
        # Get table schemas
        try:
            self.db_manager.cursor.execute("""
                SELECT table_name, sql_query, metadata
                FROM table_chunks
                ORDER BY table_name;
            """)
            
            tables = self.db_manager.cursor.fetchall()
            
            # Build schema information
            schema_info = []
            for table in tables:
                schema_info.append(f"Table: {table['table_name']}")
                schema_info.append(f"Schema:\n{table['sql_query']}")
                if table['metadata']:
                    schema_info.append(f"Description: {table['metadata'].get('description', 'N/A')}")
                schema_info.append("-" * 40)
            
            schema_text = "\n".join(schema_info)
            
        except Exception as e:
            print(f"❌ Error fetching schemas: {str(e)}\n")
            state['sql_queries'] = []
            state['error'] = str(e)
            return state
        
        # Generate SQL using LLM
        sql_generation_prompt = f"""You are an expert PostgreSQL developer. Convert the natural language question into a valid SQL query.

Database Schema:
{schema_text}

User Question: {query}

Important Guidelines:
1. Generate ONLY valid PostgreSQL SELECT queries
2. Use proper table names exactly as shown in the schema
3. Use appropriate WHERE clauses to filter data
4. Use JOINs if multiple tables are needed
5. Use aggregate functions (COUNT, AVG, SUM, etc.) when appropriate
6. Always include LIMIT clause to prevent excessive results (default LIMIT 100)
7. Use ILIKE for case-insensitive text matching
8. Format numbers and dates appropriately

CRITICAL - Handling "Top N" or "N items with condition" Queries:
- If user asks for "N items/countries/records with [condition]", prioritize returning N results
- Use ORDER BY to sort by relevant columns (scores DESC, dates DESC, etc.)
- If a threshold is mentioned (e.g., "scores more than 75"), consider it as guidance
- When threshold might be too strict, use ORDER BY + LIMIT to get top N results instead
- Example: "5 countries with scores more than 75" → Use ORDER BY score DESC LIMIT 5
- Only use strict WHERE conditions when user explicitly wants filtering (e.g., "only countries with score exactly 80")

Respond with ONLY the SQL query (or multiple queries if needed, separated by semicolons).
Do not include any explanations or markdown formatting.

Example Response:
SELECT country_name, pillar_i_score, pillar_ii_score, pillar_iii_score 
FROM governance_pillars_table_5 
WHERE country_name ILIKE '%indonesia%' 
LIMIT 10;"""

        try:
            result = self.aws_client.get_nova_response(
                prompt=sql_generation_prompt,
                model_id="us.amazon.nova-pro-v1:0"
            )
            
            if result['success']:
                sql_text = result['response'].strip()
                
                # Clean up the SQL
                # Remove markdown code blocks if present
                sql_text = re.sub(r'```sql\n?', '', sql_text)
                sql_text = re.sub(r'```\n?', '', sql_text)
                sql_text = sql_text.strip()
                
                # Split multiple queries
                sql_queries = [q.strip() + ';' for q in sql_text.split(';') if q.strip()]
                
                state['sql_queries'] = sql_queries
                
                print(f"✅ Generated {len(sql_queries)} SQL quer{'y' if len(sql_queries) == 1 else 'ies'}:\n")
                for i, sql in enumerate(sql_queries, 1):
                    print(f"Query {i}:")
                    print(sql)
                    print()
            else:
                print(f"❌ SQL generation failed: {result.get('error', 'Unknown error')}\n")
                state['sql_queries'] = []
                state['error'] = result.get('error', 'SQL generation failed')
                
        except Exception as e:
            print(f"❌ Error generating SQL: {str(e)}\n")
            state['sql_queries'] = []
            state['error'] = str(e)
        
        return state
    
    def execute_sql(self, state: TextToSQLState) -> TextToSQLState:
        """Execute SQL queries against the database via MCP"""
        print("\n" + "-" * 80)
        print("⚡ STEP 3: EXECUTING SQL QUERIES VIA MCP")
        print("-" * 80)
        
        sql_queries = state.get('sql_queries', [])
        
        if not sql_queries:
            print("⚠️ No SQL queries to execute\n")
            state['sql_results'] = []
            return state
        
        results = []
        
        for i, sql_query in enumerate(sql_queries, 1):
            print(f"\nExecuting Query {i} via MCP:")
            print(sql_query)
            
            try:
                # Use MCP client if connected, otherwise fallback to direct connection
                if self.mcp_client.is_connected():
                    print("   Using MCP server for query execution...")
                    mcp_result = self.mcp_client.execute_query(sql_query)
                    
                    if mcp_result.get('success'):
                        result_data = mcp_result.get('rows', [])
                        results.append({
                            'query': sql_query,
                            'success': True,
                            'rows': result_data,
                            'row_count': mcp_result.get('row_count', len(result_data))
                        })
                        print(f"✅ Success (via MCP): Retrieved {len(result_data)} row(s)")
                    else:
                        # Get detailed error message
                        error_msg = mcp_result.get('error', mcp_result.get('message', 'Unknown error'))
                        print(f"❌ Error (via MCP): {error_msg}")
                        
                        # Try fallback to direct connection
                        print("   🔄 Attempting fallback to direct database connection...")
                        try:
                            self.db_manager.cursor.execute(sql_query)
                            rows = self.db_manager.cursor.fetchall()
                            
                            if rows:
                                result_data = [dict(row) for row in rows]
                                results.append({
                                    'query': sql_query,
                                    'success': True,
                                    'rows': result_data,
                                    'row_count': len(result_data)
                                })
                                print(f"✅ Success (fallback): Retrieved {len(result_data)} row(s)")
                            else:
                                results.append({
                                    'query': sql_query,
                                    'success': True,
                                    'rows': [],
                                    'row_count': 0
                                })
                                print("✅ Success (fallback): No rows returned")
                        except Exception as fallback_error:
                            print(f"❌ Fallback also failed: {str(fallback_error)}")
                            results.append({
                                'query': sql_query,
                                'success': False,
                                'error': f"MCP error: {error_msg}, Fallback error: {str(fallback_error)}",
                                'rows': [],
                                'row_count': 0
                            })
                else:
                    # Fallback to direct database connection
                    print("⚠️ MCP not connected, using direct database connection")
                    self.db_manager.cursor.execute(sql_query)
                    rows = self.db_manager.cursor.fetchall()
                    
                    if rows:
                        result_data = [dict(row) for row in rows]
                        results.append({
                            'query': sql_query,
                            'success': True,
                            'rows': result_data,
                            'row_count': len(result_data)
                        })
                        print(f"✅ Success (direct): Retrieved {len(result_data)} row(s)")
                    else:
                        results.append({
                            'query': sql_query,
                            'success': True,
                            'rows': [],
                            'row_count': 0
                        })
                        print("✅ Success (direct): No rows returned")
                    
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                results.append({
                    'query': sql_query,
                    'success': False,
                    'error': str(e),
                    'rows': [],
                    'row_count': 0
                })
        
        state['sql_results'] = results
        print()
        
        return state
    
    def format_results(self, state: TextToSQLState) -> TextToSQLState:
        """Format SQL results into human-readable text"""
        print("\n" + "-" * 80)
        print("📊 STEP 4: FORMATTING RESULTS")
        print("-" * 80)
        
        sql_results = state.get('sql_results', [])
        
        if not sql_results:
            state['combined_result'] = "No SQL results available."
            return state
        
        formatted_parts = []
        
        for i, result in enumerate(sql_results, 1):
            if result['success']:
                if result['row_count'] > 0:
                    formatted_parts.append(f"Query {i} Results ({result['row_count']} row(s)):")
                    
                    # Format as table
                    rows = result['rows']
                    if rows:
                        # Get column names
                        columns = list(rows[0].keys())
                        
                        # Create formatted table
                        formatted_parts.append("| " + " | ".join(columns) + " |")
                        formatted_parts.append("|" + "|".join(["---"] * len(columns)) + "|")
                        
                        for row in rows[:10]:  # Limit to first 10 rows in display
                            formatted_parts.append("| " + " | ".join([str(row.get(col, 'N/A')) for col in columns]) + " |")
                        
                        if result['row_count'] > 10:
                            formatted_parts.append(f"... and {result['row_count'] - 10} more rows")
                else:
                    formatted_parts.append(f"Query {i}: No results found.")
            else:
                formatted_parts.append(f"Query {i} failed: {result.get('error', 'Unknown error')}")
            
            formatted_parts.append("")  # Empty line between queries
        
        combined = "\n".join(formatted_parts)
        state['combined_result'] = combined
        
        print("✅ Results formatted successfully\n")
        
        return state
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a natural language query through the Text-to-SQL workflow
        
        Args:
            query: User's natural language question
            
        Returns:
            Dictionary containing SQL results and metadata
        """
        print("\n" + "=" * 80)
        print("🚀 STARTING TEXT-TO-SQL WORKFLOW")
        print("=" * 80)
        
        # Initial state
        initial_state = {
            'query': query,
            'requires_sql': False,
            'sql_queries': [],
            'sql_results': [],
            'combined_result': '',
            'error': '',
            'reasoning': ''
        }
        
        # Run workflow
        final_state = self.workflow.invoke(initial_state)
        
        print("\n" + "=" * 80)
        print("✅ TEXT-TO-SQL WORKFLOW COMPLETED")
        print("=" * 80 + "\n")
        
        return {
            'query': query,
            'requires_sql': final_state.get('requires_sql', False),
            'reasoning': final_state.get('reasoning', ''),
            'sql_queries': final_state.get('sql_queries', []),
            'sql_results': final_state.get('sql_results', []),
            'formatted_result': final_state.get('combined_result', ''),
            'error': final_state.get('error', '')
        }


def main():
    """Main entry point for Agent 5"""
    # Initialize agent
    agent = TextToSQLAgent()
    
    # Test queries
    test_queries = [
        "What is the pillar score for Indonesia?",
        "Explain the role of business readiness",
        "Compare the pillar scores between Turkey and Mali",
        "Explain business readiness. Also, what are the top 5 countries by pillar I score?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print("\n" + "=" * 80)
        print(f"TEST QUERY {i}")
        print("=" * 80)
        
        result = agent.process_query(query)
        
        print("\n📊 RESULTS:")
        print(f"   Requires SQL: {result['requires_sql']}")
        print(f"   Reasoning: {result['reasoning']}")
        
        if result['requires_sql']:
            print(f"   SQL Queries Generated: {len(result['sql_queries'])}")
            print(f"\n   Formatted Results:\n{result['formatted_result']}")
        
        if result['error']:
            print(f"   ⚠️ Error: {result['error']}")
        
        print("\n")
    
    # Close database connection
    agent.db_manager.close()


if __name__ == "__main__":
    main()
