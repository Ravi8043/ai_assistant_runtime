CHUNK_SUMMARY_PROMPT = """You are an expert reading assistant.

Please summarize the following section of a document. 
Capture the main points, key arguments, and any critical details.

Section content:
{chunk_text}

Return only the summary.
"""

SYNTHESIZE_REPORT_PROMPT = """You are an expert reading assistant.

I have provided summaries of several sections of a document.
Please synthesize them into a single, cohesive, and comprehensive report.

Section Summaries:
{summaries}

Return the final report formatted as a markdown document.
"""
