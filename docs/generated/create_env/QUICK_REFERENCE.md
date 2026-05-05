# Quick Reference Guide - create_env Agent

## Installation

```bash
# Navigate to the repo
cd C:\Data\Repos\chandmare_ai_agents

# Install the package
pip install -e packages/create_env
```

## Basic Commands

### List all available options
```bash
python -m create_env scan --help
```

### Scan a local project
```bash
python -m create_env scan C:\path\to\your\project
```

### Scan with specific conda environment
```bash
python -m create_env scan C:\path\to\your\project --env-name myenv
```

### Scan remote git repository
```bash
python -m create_env scan C:\output\path --git-repo https://github.com/user/repo.git
```

### Scan remote repo and save to specific conda env
```bash
python -m create_env scan C:\output\path --env-name myenv --git-repo https://github.com/user/repo.git
```

## Output Files

The agent generates three files in the scanned project directory:

1. **requirements.txt** - pip format with exact versions
   ```
   numpy==2.1.3
   pandas==2.3.2
   scikit-learn==1.7.2
   ```

2. **conda.yaml** - conda environment format
   ```yaml
   name: null
   channels:
     - defaults
     - conda-forge
   dependencies:
     - numpy=2.1.3
     - pandas=2.3.2
   ```

3. **dependency_warnings.txt** - Issues and missing packages report

## Running Tests

### All tests
```bash
python -m pytest tests/create_env_test/ -v
```

### Scanner tests only
```bash
python -m pytest tests/create_env_test/test_scanner.py -v
```

### Generator tests only
```bash
python -m pytest tests/create_env_test/test_generator.py -v
```

### CLI tests only
```bash
python -m pytest tests/create_env_test/test_cli.py -v
```

### Run with coverage
```bash
python -m pytest tests/create_env_test/ --cov=packages/create_env
```

## Package Structure Summary

```
chandmare_ai_agents/
├── agents/
│   └── create_env_agent.md         # Specification document
├── packages/
│   └── create_env/                 # Main package (installable)
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── scanner.py
│       ├── generator.py
│       ├── setup.py
│       └── README.md
├── tests/
│   └── create_env_test/            # Test suite
│       ├── conftest.py
│       ├── test_scanner.py
│       ├── test_generator.py
│       ├── test_cli.py
│       └── pytest.ini
└── IMPLEMENTATION_SUMMARY.md       # Detailed implementation doc
```

## Example Workflow

### Step 1: Navigate to agent repo
```bash
cd C:\Data\Repos\chandmare_ai_agents
```

### Step 2: Install the package
```bash
pip install -e packages/create_env
```

### Step 3: Create a test project
```bash
mkdir C:\my_project
cd C:\my_project
echo import numpy > main.py
echo import pandas >> main.py
```

### Step 4: Run the agent
```bash
python -m create_env scan C:\my_project
```

### Step 5: Check outputs
```bash
cat C:\my_project\requirements.txt
cat C:\my_project\conda.yaml
cat C:\my_project\dependency_warnings.txt
```

## Troubleshooting

### "Could not resolve version for package"
- Make sure the package is installed in your conda/pip environment
- Use `--env-name` to specify a different environment

### "No Python files found"
- Ensure the directory contains `.py` files
- Check the path is correct

### Git clone fails
- Verify the git URL is correct and accessible
- Make sure git is installed on your system

### Import remappings not working
- Remappings are hardcoded for: sklearn, cv2, yaml, PIL, bs4
- Other packages use their import name as the package name

## Support

For detailed specifications, see: `agents/create_env_agent.md`
For implementation details, see: `IMPLEMENTATION_SUMMARY.md`
For package usage, see: `packages/create_env/README.md`

