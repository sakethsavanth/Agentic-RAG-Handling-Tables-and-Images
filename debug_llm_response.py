"""
Debug Helper for LLM Response Quality
Use this to understand what context is being sent to the LLM
"""

def analyze_chunks_for_query(reranked_chunks, query):
    """
    Analyze retrieved chunks to see if they contain relevant information
    
    Args:
        reranked_chunks: List of reranked chunks
        query: User query
    """
    print("\n" + "="*80)
    print("🔍 CHUNK ANALYSIS FOR QUERY")
    print("="*80)
    print(f"Query: {query}\n")
    
    # Extract keywords from query
    keywords = [w.lower() for w in query.split() if len(w) > 3]
    print(f"🔑 Keywords extracted: {', '.join(keywords)}\n")
    
    print("📚 CHUNK RELEVANCE ANALYSIS:")
    print("-"*80)
    
    for i, chunk in enumerate(reranked_chunks[:10], 1):
        content_lower = chunk['content'].lower()
        
        # Count keyword matches
        matches = sum(1 for kw in keywords if kw in content_lower)
        match_percent = (matches / len(keywords)) * 100 if keywords else 0
        
        # Check for numbers (for quantitative questions)
        has_numbers = any(char.isdigit() for char in chunk['content'])
        
        print(f"\n[{i}] {chunk['chunk_id']}")
        print(f"    Type: {chunk['chunk_type']}")
        print(f"    Score: {chunk.get('final_score', 0):.4f}")
        print(f"    Source: {chunk['source_document']}")
        print(f"    Keyword Matches: {matches}/{len(keywords)} ({match_percent:.0f}%)")
        print(f"    Contains Numbers: {'✓' if has_numbers else '✗'}")
        print(f"    Content Length: {len(chunk['content'])} chars")
        print(f"    Preview: {chunk['content'][:150]}...")
        
        # Highlight matching keywords
        if matches > 0:
            found_keywords = [kw for kw in keywords if kw in content_lower]
            print(f"    ✅ Found keywords: {', '.join(found_keywords)}")
    
    print("\n" + "="*80)
    print("📊 SUMMARY:")
    print(f"   Total chunks analyzed: {len(reranked_chunks[:10])}")
    print(f"   Text chunks: {sum(1 for c in reranked_chunks[:10] if c['chunk_type'] == 'text')}")
    print(f"   Table chunks: {sum(1 for c in reranked_chunks[:10] if c['chunk_type'] == 'table')}")
    print(f"   Image chunks: {sum(1 for c in reranked_chunks[:10] if c['chunk_type'] == 'image')}")
    
    avg_matches = sum(sum(1 for kw in keywords if kw in c['content'].lower()) 
                     for c in reranked_chunks[:10]) / len(reranked_chunks[:10])
    print(f"   Avg keyword matches per chunk: {avg_matches:.1f}/{len(keywords)}")
    
    chunks_with_numbers = sum(1 for c in reranked_chunks[:10] 
                             if any(char.isdigit() for char in c['content']))
    print(f"   Chunks containing numbers: {chunks_with_numbers}/10")
    print("="*80 + "\n")


def suggest_improvements(reranked_chunks, query):
    """Suggest improvements based on chunk analysis"""
    keywords = [w.lower() for w in query.split() if len(w) > 3]
    
    # Check if query asks for numbers but chunks lack numbers
    quantitative_words = ['how much', 'how many', 'what is the', 'number', 'rate', 'percentage', 'statistics']
    is_quantitative = any(qw in query.lower() for qw in quantitative_words)
    
    chunks_with_numbers = sum(1 for c in reranked_chunks[:5] 
                             if any(char.isdigit() for char in c['content']))
    
    print("💡 SUGGESTIONS:")
    print("-"*80)
    
    if is_quantitative and chunks_with_numbers < 2:
        print("⚠️ Query asks for quantitative data but top chunks lack numbers")
        print("   → Check if TABLE chunks are ranked high enough")
        print("   → Consider increasing table weight in reranking")
    
    # Check keyword matches
    avg_matches = sum(sum(1 for kw in keywords if kw in c['content'].lower()) 
                     for c in reranked_chunks[:5]) / 5
    
    if avg_matches < 1:
        print("⚠️ Low keyword matches in top 5 chunks")
        print("   → Retrieval may not be finding relevant documents")
        print("   → Consider query expansion or synonym matching")
    
    # Check content length
    avg_length = sum(len(c['content']) for c in reranked_chunks[:5]) / 5
    
    if avg_length < 200:
        print("⚠️ Chunks are very short (avg < 200 chars)")
        print("   → May not contain enough context")
        print("   → Consider adjusting chunking strategy")
    
    print("-"*80 + "\n")


# Example usage:
if __name__ == "__main__":
    # This would be called with actual chunks and query
    print("""
Usage in your code:

from debug_llm_response import analyze_chunks_for_query, suggest_improvements

# In chatbot_orchestrator.py, add before _generate_llm_response:
analyze_chunks_for_query(reranked_chunks, query)
suggest_improvements(reranked_chunks, query)

# Then proceed with normal response generation
response = self._generate_llm_response(query, reranked_chunks)
    """)
