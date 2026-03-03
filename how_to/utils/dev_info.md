## Development Info

### 

## Adding a new library or module to the project

Make sure to add it to the `pyproject.toml` file if it is the main root directory of the project.

```toml
[tool.setuptools]
py-modules = [
    # ... existing modules
    "world_data",
    "game",
    "new_agents" # <--- ADD THE NEW FOLDER/MODULE HERE
]
```

What this does is add the new module to the project so that it can be imported and used in the code.

