from .base import Tool


class ListDirTool(Tool):
    name = "list_dir"
    description = (
        "List files and directories under a workspace path. "
        "Use '.' for the repository root. Directory names end with '/'."
    )

    def __init__(self, environment):
        self.environment = environment

    def schema(self):
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Workspace-relative directory path. Use '.' for root."
                        ),
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    def execute(self, path: str) -> str:
        return self.environment.list_dir(path or ".")


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read a repository file."

    def __init__(self, environment):
        self.environment = environment

    def schema(self):
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    def execute(self, path: str) -> str:
        return self.environment.read_file(path)


class WriteFileTool(Tool):
    name = "write_file"
    description = "Write or overwrite a repository file with the given content."

    def __init__(self, environment):
        self.environment = environment

    def schema(self):
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                    },
                    "content": {
                        "type": "string",
                    },
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    def execute(self, path: str, content: str) -> str:
        self.environment.write_file(path, content)
        return f"Wrote {path}"
