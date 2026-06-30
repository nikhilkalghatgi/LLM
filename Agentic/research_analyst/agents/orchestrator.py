"""ReAct orchestrator — pure-Python Thought/Action/Observation loop over sub-agents."""

import re
from typing import Dict, List, Optional

import ollama

from retrieval.reranker import HybridReranker
from agents.retriever_agent import RetrieverAgent
from agents.analyst_agent import AnalystAgent
from agents.critic_agent import CriticAgent


SYSTEM_PROMPT = """You are a research orchestrator that answers research questions by coordinating specialist tools.

At each step you MUST output EXACTLY three lines in this format:

Thought: <your reasoning about what to do next>
Action: <one of: retriever, analyst, critic, finish>
Action Input: <the input to pass to that tool>

Available tools:
- retriever: Search the document corpus for relevant passages. Input should be the search query.
- analyst: Analyse retrieved context to answer the question. Input should be the research question.
- critic: Review an analysis for accuracy. Input should be the research question.
- finish: Return the final answer. Input should be the complete final report.

Workflow guidelines:
1. Start by using 'retriever' to find relevant passages.
2. Then use 'analyst' to produce a structured analysis from the retrieved context.
3. Then use 'critic' to verify the analysis.
4. If the critic fails the analysis, you may revise and re-analyse.
5. When satisfied, use 'finish' with the final report as input.

IMPORTANT: You must ALWAYS output exactly the three lines (Thought, Action, Action Input). Do not output anything else."""


class ReActOrchestrator:
    """Pure-Python ReAct loop that coordinates retriever, analyst, and critic agents."""

    def __init__(self, config: dict, reranker: HybridReranker) -> None:
        self.config = config
        self.model = config.get("llm_model", "mistral")
        self.base_url = config.get("llm_base_url", "http://localhost:11434")
        self.max_steps = config.get("max_react_steps", 6)
        self.client = ollama.Client(host=self.base_url)

        # Initialise sub-agents
        self.retriever_agent = RetrieverAgent(reranker, config)
        self.analyst_agent = AnalystAgent(config)
        self.critic_agent = CriticAgent(config)

        # Accumulated context passed between steps
        self._context: Dict[str, Optional[str]] = {
            "formatted_context": None,
            "analysis": None,
            "feedback": None,
            "retrieved_chunks": None,
        }

    def _call_llm(self, prompt: str) -> str:
        """Call Ollama with the given prompt and return the response text."""
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return response["message"]["content"]

    def _parse_action(self, llm_output: str) -> Dict:
        """Parse Thought / Action / Action Input from the LLM output.

        Returns:
            Dict with keys: tool, input, reasoning.
        """
        thought = ""
        action = ""
        action_input = ""

        thought_match = re.search(r"Thought:\s*(.+)", llm_output)
        action_match = re.search(r"Action:\s*(.+)", llm_output)
        input_match = re.search(
            r"Action Input:\s*(.+)", llm_output, re.DOTALL
        )

        if thought_match:
            thought = thought_match.group(1).strip()
        if action_match:
            action = action_match.group(1).strip().lower()
        if input_match:
            action_input = input_match.group(1).strip()

        valid_tools = {"retriever", "analyst", "critic", "finish"}
        if action not in valid_tools:
            return {
                "tool": "finish",
                "input": llm_output,
                "reasoning": "parse error — could not identify a valid action",
            }

        return {
            "tool": action,
            "input": action_input,
            "reasoning": thought,
        }

    def _dispatch(self, action: Dict, context: Dict) -> str:
        """Route the parsed action to the appropriate sub-agent.

        Returns:
            Observation string to feed back into the next LLM call.
        """
        tool = action["tool"]
        tool_input = action["input"]

        if tool == "retriever":
            result = self.retriever_agent.run(query=tool_input)
            self._context["formatted_context"] = result["formatted_context"]
            self._context["retrieved_chunks"] = result["chunks"]
            num_chunks = len(result["chunks"])
            return (
                f"Retrieved {num_chunks} relevant passages.\n\n"
                f"{result['formatted_context']}"
            )

        elif tool == "analyst":
            ctx = self._context.get("formatted_context", "")
            if not ctx:
                return "Error: No context available. Run retriever first."
            result = self.analyst_agent.run(query=tool_input, context=ctx)
            self._context["analysis"] = result["analysis"]
            citations = ", ".join(result["citations"]) if result["citations"] else "none"
            return (
                f"Analysis complete. Citations found: {citations}\n\n"
                f"{result['analysis']}"
            )

        elif tool == "critic":
            analysis = self._context.get("analysis", "")
            ctx = self._context.get("formatted_context", "")
            if not analysis:
                return "Error: No analysis to critique. Run analyst first."
            result = self.critic_agent.run(
                query=tool_input, analysis=analysis, context=ctx
            )
            verdict = "PASS" if result["passed"] else "FAIL"
            self._context["feedback"] = result["feedback"]
            if result["revised_analysis"]:
                self._context["analysis"] = result["revised_analysis"]
            return (
                f"Critic verdict: {verdict}\n"
                f"Feedback: {result['feedback']}"
            )

        elif tool == "finish":
            return tool_input

        return f"Unknown tool: {tool}"

    def _build_step_prompt(self, query: str, trace: List[Dict]) -> str:
        """Build the prompt for the next ReAct step, including prior history."""
        prompt_parts: List[str] = [f"Research Question: {query}\n"]

        # Append accumulated context summary
        if self._context["formatted_context"]:
            prompt_parts.append(
                "== Retrieved Context (available for analysis) ==\n"
                f"{self._context['formatted_context']}\n"
            )
        if self._context["analysis"]:
            prompt_parts.append(
                "== Current Analysis ==\n"
                f"{self._context['analysis']}\n"
            )
        if self._context["feedback"]:
            prompt_parts.append(
                "== Critic Feedback ==\n"
                f"{self._context['feedback']}\n"
            )

        # Append step history
        if trace:
            prompt_parts.append("== Prior Steps ==")
            for step in trace:
                prompt_parts.append(
                    f"Step {step['step']}:\n"
                    f"  Thought: {step['thought']}\n"
                    f"  Action: {step['action']}\n"
                    f"  Action Input: {step['action_input']}\n"
                    f"  Observation: {step['observation'][:500]}\n"
                )

        prompt_parts.append(
            "\nBased on the above, decide what to do next. "
            "Output Thought, Action, and Action Input."
        )

        return "\n".join(prompt_parts)

    def run(self, query: str) -> Dict:
        """Execute the full ReAct loop for a research query.

        Returns:
            Dict with keys:
                report — final answer / analysis text
                trace — list of step dicts
                steps_taken — int
        """
        return self.run_with_callback(query, step_callback=None)

    def run_with_callback(self, query: str, step_callback=None) -> Dict:
        """Execute the ReAct loop, optionally emitting each step to a callback.

        Args:
            query: The research question.
            step_callback: Optional ``fn(step_dict)`` invoked after every step.
                Used by the SSE endpoint to stream the trace as it is produced.

        Returns:
            Dict with keys: report, trace, steps_taken, analysis, feedback,
            retrieved_chunks.
        """
        # Reset context for each new query
        self._context = {
            "formatted_context": None,
            "analysis": None,
            "feedback": None,
            "retrieved_chunks": None,
        }

        trace: List[Dict] = []
        report = ""

        for step_num in range(1, self.max_steps + 1):
            prompt = self._build_step_prompt(query, trace)
            llm_output = self._call_llm(prompt)
            action = self._parse_action(llm_output)

            # Print step in real time
            print(f"\n{'='*60}")
            print(f"Step {step_num}")
            print(f"{'='*60}")
            print(f"Thought: {action['reasoning']}")
            print(f"Action:  {action['tool']}")
            print(f"Input:   {action['input'][:200]}")

            if action["tool"] == "finish":
                report = action["input"]
                # Use the latest analysis if finish input is sparse
                if len(report) < 50 and self._context.get("analysis"):
                    report = self._context["analysis"]
                step_record = {
                    "step": step_num,
                    "thought": action["reasoning"],
                    "action": action["tool"],
                    "action_input": action["input"],
                    "observation": "Final report delivered.",
                }
                trace.append(step_record)
                if step_callback is not None:
                    step_callback(step_record)
                print("Observation: Final report delivered.")
                break

            observation = self._dispatch(action, self._context)
            print(f"Observation: {observation[:300]}...")

            step_record = {
                "step": step_num,
                "thought": action["reasoning"],
                "action": action["tool"],
                "action_input": action["input"],
                "observation": observation,
            }
            trace.append(step_record)
            if step_callback is not None:
                step_callback(step_record)

        # If loop exhausted without finish, use latest analysis
        if not report:
            report = self._context.get("analysis") or "No analysis produced."

        return {
            "report": report,
            "trace": trace,
            "steps_taken": len(trace),
            "analysis": self._context.get("analysis"),
            "feedback": self._context.get("feedback"),
            "retrieved_chunks": self._context.get("retrieved_chunks") or [],
        }
