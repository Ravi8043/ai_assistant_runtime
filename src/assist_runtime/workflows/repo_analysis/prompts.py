REPO_ANALYSIS_PROMPT = """You are an expert system architect analyzing a code repository.

Given the following raw directory and file information, provide a comprehensive architecture overview.

Focus on:
1. The primary purpose of the repository.
2. The high-level architecture and component breakdown.
3. Key dependency patterns and frameworks used.
4. An assessment of code organization and modularity.

Raw Data:
{scanned_data}

Return your response as a well-structured markdown document. Do NOT include any filler text.
"""
