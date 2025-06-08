# pa-permission-template-generator
Generates permission templates (e.g., JSON, YAML) based on existing permission assignments, facilitating consistent permission application across similar roles or resources. Uses a Jinja2 template to write the output. - Focused on Tools for analyzing and assessing file system permissions

## Install
`git clone https://github.com/ShadowStrikeHQ/pa-permission-template-generator`

## Usage
`./pa-permission-template-generator [params]`

## Parameters
- `-h`: Show help message and exit
- `--source-dir`: Path to the directory to analyze permissions from.
- `--output-file`: Path to the output file to write the permission template to.
- `--template-file`: Path to the Jinja2 template file to use for generating the template.
- `--exclude-patterns`: List of file patterns to exclude from permission analysis (e.g., 
- `--output-format`: No description provided

## License
Copyright (c) ShadowStrikeHQ
