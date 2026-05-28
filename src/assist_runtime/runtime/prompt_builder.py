import json
from typing import Any

class PromptBuilder:
    """Centralizes prompt construction and context assembly."""

    @staticmethod
    def build_file_summary_prompt(file_path: str, code_content: str) -> str:
        return f"""You are an advanced system extraction engine parsing a single codebase asset.
Extract the structural intent, interface declarations, and run scripts found directly in this code.

File Path: {file_path}
Code Block:
{code_content}


RESPOND STRICTLY IN VALID JSON FORMAT MATCHING THIS EXACT SCHEMA. DO NOT ESCAPE OUTSIDE THE JSON:
{{
  "purpose": "A concise two to three-sentence description of the file's primary mandate.",
  "exposed_commands": [
    {{
      "command": "The exact script string or execution line if this file declares or runs one (e.g., 'bun test:evals')",
      "description": "Short inline bash comment explanation of what the command achieves."
    }}
  ],
  "architectural_constraints": ["List of environmental prerequisites, ports, or critical failure modes found in code comments/logic"],
  "sub_modules": ["List of sub-directories, files, or symbols imported/exported from here"]
}}
"""

    @staticmethod
    def build_module_summary_prompt(module_name: str, context: str) -> str:
        return f"""You are evaluating structural system architecture domains.
Review the structural JSON metrics extracted from files inside the '{module_name}' directory. 

Your objective is to synthesize these details into a unified directory overview.

Directory Domain: {module_name}
Extracted Source Metrics:
{context}

YOUR RESPONSE MUST STRICTLY FOLLOW THIS MARKDOWN BREAKDOWN SCHEMA:
### Module: {module_name}
- **Mandate**: A 2-3 sentence description of what this module encapsulates.
- **Commands Introduced**: Compile any shell/run commands found in this module. Format exactly as a bulleted list of text lines.
- **System Constraints**: List any ports, env variables, or operational boundaries found here.
- **ASCII Directory Segment**: Formulate a tight text-based representation of the files in this module (e.g., └── code.ts # comment) based on the input paths.
"""

    @staticmethod
    def build_repo_analysis_prompt(context: str) -> str:
        return f"""You are a Principal Software Architect compiling the master production runbook and structural blueprint for a system.

Use the provided module-level specifications to construct a clean, highly actionable markdown document.

System Modules Specifications:
{context}

OUTPUT FORMAT SPECIFICATIONS:
1. Start directly with a `# Project Name` title based on the context.
2. Provide a `## Commands` section. Collect ALL commands from the modules and present them inside a single clean bash code block with aligned, clean trailing text comments.
3. Provide an indented text block explaining any critical environmental variables or authentication dependencies discovered.
4. Provide a `## Project Structure` section. Construct a clean, unified ASCII file hierarchy tree mapping the entire system cleanly based on the module inputs. Append an inline text comment to the main directory folders explaining their technical mandate.
5. Provide sections detailing specific operational policies, testing constraints, or security stacks found in the module data.

Do NOT introduce your response with filler text like 'Sure, here is the summary'. Start immediately with the markdown syntax.
"""

    # ============================================================
    # GENERAL DOCUMENT & QA WORKFLOWS
    # ============================================================

    @staticmethod
    def build_chunk_summary_prompt(chunk_text: str) -> str:
        return f"""You are an expert reading assistant.

Please summarize the following section of a document. 
Capture the main points, key arguments, and critical technical details.

Section content:
{chunk_text}

Return only the summary text without any conversational filler.
"""

    @staticmethod
    def build_synthesize_report_prompt(summaries: str) -> str:
        return f"""You are an expert technical writer.

Synthesize the following document section summaries into a single, cohesive, and comprehensive report.
Ensure logical flow between the sections and eliminate redundant information.

Section Summaries:
{summaries}

Return the final report formatted as a clean markdown document.
"""

    @staticmethod
    def build_repo_qa_prompt(context: str, question: str) -> str:
        return f"""You are a senior developer answering a technical question about your codebase.

Use the provided context to answer the user's question accurately. 
If the context does not contain enough information to answer definitively, state exactly what information is missing.

Context:
{context}

Question: {question}

Provide a clear, concise answer. Include exact code snippets or file references from the context if they are relevant.
"""
