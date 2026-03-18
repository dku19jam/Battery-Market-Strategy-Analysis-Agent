"""Prompt asset placeholders for workflow stages."""

WORKFLOW_COORDINATION_PROMPT = "Coordinate distributed workflow handoffs and preserve reproducibility metadata."
RETRIEVAL_PROMPT_TEMPLATE = "Search {company} evidence for topic '{topic}' using local corpus first."
CURATION_PROMPT_TEMPLATE = "Group evidence by topic, deduplicate, and keep the highest-trust items."
ANALYSIS_PROMPT_TEMPLATE = "Analyze one company only and return structured JSON."
COMPARISON_PROMPT_TEMPLATE = "Compare two company analyses and return structured JSON."
REPORT_PROMPT_TEMPLATE = "Assemble the final Korean report with SUMMARY first and REFERENCE last."
