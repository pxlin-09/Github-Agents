from __future__ import annotations

from pathlib import Path

from issue_agent.runtime.trajectory import Trajectory


def test_trajectory_add_step_and_save(tmp_path: Path):
    traj = Trajectory(task="fix it")
    traj.add_step(tool="list_dir", arguments={"path": "."}, output="a.py")
    traj.add_step(tool="read_file", arguments={"path": "a.py"}, output="print(1)")

    data = traj.to_dict()
    assert data["task"] == "fix it"
    assert [step["step"] for step in data["steps"]] == [1, 2]
    assert data["steps"][0]["tool"] == "list_dir"

    path = traj.save(tmp_path)
    assert path.exists()
    assert path.suffix == ".json"
    assert '"list_dir"' in path.read_text(encoding="utf-8")
