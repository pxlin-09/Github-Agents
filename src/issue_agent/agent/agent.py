import json
import logging

from issue_agent.agent.prompts import SYSTEM_PROMPT
from issue_agent.runtime.cost import CostLimitExceeded, CostTracker
from issue_agent.runtime.trajectory import Trajectory

logger = logging.getLogger(__name__)


class CodingAgent:
    def __init__(
        self,
        model,
        tools,
        max_steps=30,
        trajectory_dir=None,
        verbose=True,
        cost_tracker: CostTracker | None = None,
    ):
        self.model = model
        self.tools = tools
        self.max_steps = max_steps
        self.trajectory_dir = trajectory_dir
        self.verbose = verbose
        self.cost_tracker = cost_tracker

    def log_action(self, func_name, arg, output, prune=200, level=logging.INFO):
        if not self.verbose:
            return
        arg_text = str(arg)
        output_text = str(output)
        if len(arg_text) > prune:
            arg_text = arg_text[:prune] + "..."
        if len(output_text) > prune:
            output_text = output_text[:prune] + "..."
        message = (
            f"{func_name} called with arguments {arg_text} "
            f"and output {output_text}"
        )
        logging.log(level, message)

    def run(self, task):
        trajectory = Trajectory(task=task)
        inputs = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": task,
            },
        ]

        try:
            for _ in range(self.max_steps):
                if self.cost_tracker is not None:
                    self.cost_tracker.ensure_can_call()

                response = self.model.generate(
                    input_items=inputs,
                    tools=self.tools.schemas(),
                )

                if self.cost_tracker is not None:
                    usage = getattr(response, "usage", None)
                    self.cost_tracker.record_usage(usage)

                calls = [
                    item
                    for item in response.output
                    if item.type == "function_call"
                ]

                if not calls:
                    return response.output_text

                inputs.extend(response.output)

                for call in calls:
                    args = json.loads(call.arguments)

                    result = self.tools.execute(
                        call.name,
                        args,
                    )

                    trajectory.add_step(
                        tool=call.name,
                        arguments=args,
                        output=result,
                    )

                    inputs.append({
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": result,
                    })

                    self.log_action(call.name, args, result)

            raise RuntimeError("Agent reached maximum steps")
        except CostLimitExceeded:
            logger.error(
                "Stopping agent: cost limit reached "
                "(spent=$%.4f max=$%.4f)",
                self.cost_tracker.spent_usd if self.cost_tracker else 0.0,
                self.cost_tracker.max_cost_usd if self.cost_tracker else 0.0,
            )
            raise
        finally:
            self._save(trajectory)

    def _save(self, trajectory: Trajectory) -> None:
        if self.trajectory_dir is None:
            return
        path = trajectory.save(self.trajectory_dir)
        print(f"Saved trajectory: {path}")
