class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, tool):
        self._tools[tool.name] = tool

    def schemas(self):
        return [
            tool.schema()
            for tool in self._tools.values()
        ]

    def execute(self, name, arguments):
        tool = self._tools.get(name)

        if tool is None:
            return f"Error: Unknown tool: {name}"

        try:
            return tool.execute(**arguments)
        except (OSError, ValueError, RuntimeError) as exc:
            return f"Error: {exc}"
