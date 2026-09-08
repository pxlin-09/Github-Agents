import json
import logging

from issue_agent.agent.prompts import SYSTEM_PROMPT
from issue_agent.runtime.trajectory import Trajectory


class CodingAgent:
    def __init__(
        self,
        model,
        tools,
        max_steps=30,
        trajectory_dir=None,
        verbose=True,
    ):
        self.model = model
        self.tools = tools
        self.max_steps = max_steps
        self.trajectory_dir = trajectory_dir
        self.verbose = verbose

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
                response = self.model.generate(
                    input_items=inputs,
                    tools=self.tools.schemas(),
                )

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
        finally:
            self._save(trajectory)

    def _save(self, trajectory: Trajectory) -> None:
        if self.trajectory_dir is None:
            return
        path = trajectory.save(self.trajectory_dir)
        print(f"Saved trajectory: {path}")
