import argparse
import json
import logging
import os
import stat
import sys
from typing import List, Dict, Any

import jinja2
from pathspec import PathSpec

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

def setup_argparse() -> argparse.ArgumentParser:
    """
    Sets up the argument parser for the tool.

    Returns:
        argparse.ArgumentParser: The argument parser object.
    """
    parser = argparse.ArgumentParser(
        description="Generates permission templates based on existing permission assignments."
    )
    parser.add_argument(
        "--source-dir",
        type=str,
        required=True,
        help="Path to the directory to analyze permissions from.",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        required=True,
        help="Path to the output file to write the permission template to.",
    )
    parser.add_argument(
        "--template-file",
        type=str,
        required=True,
        help="Path to the Jinja2 template file to use for generating the template.",
    )
    parser.add_argument(
        "--exclude-patterns",
        type=str,
        nargs="*",
        default=[],
        help="List of file patterns to exclude from permission analysis (e.g., '*.log', 'temp/*').",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        choices=["json", "yaml"],
        default="json",
        help="Format of the output file (json or yaml).  Requires PyYAML to be installed for yaml.",
    )
    return parser


def get_file_permissions(file_path: str) -> Dict[str, Any]:
    """
    Retrieves file permissions information for a given file path.

    Args:
        file_path (str): The path to the file.

    Returns:
        Dict[str, Any]: A dictionary containing file permission information.
                       Returns None if an error occurs.
    """
    try:
        stat_info = os.stat(file_path)
        permissions = {
            "user": {
                "read": bool(stat_info.st_mode & stat.S_IRUSR),
                "write": bool(stat_info.st_mode & stat.S_IWUSR),
                "execute": bool(stat_info.st_mode & stat.S_IXUSR),
            },
            "group": {
                "read": bool(stat_info.st_mode & stat.S_IRGRP),
                "write": bool(stat_info.st_mode & stat.S_IWGRP),
                "execute": bool(stat_info.st_mode & stat.S_IXGRP),
            },
            "other": {
                "read": bool(stat_info.st_mode & stat.S_IROTH),
                "write": bool(stat_info.st_mode & stat.S_IWOTH),
                "execute": bool(stat_info.st_mode & stat.S_IXOTH),
            },
            "owner": stat_info.st_uid,
            "group_id": stat_info.st_gid,
            "mode": stat.filemode(stat_info.st_mode),
            "file_size": stat_info.st_size
        }
        return permissions
    except OSError as e:
        logging.error(f"Error getting permissions for {file_path}: {e}")
        return None


def analyze_directory_permissions(
    source_dir: str, exclude_patterns: List[str]
) -> List[Dict[str, Any]]:
    """
    Analyzes file permissions in a directory, excluding specified patterns.

    Args:
        source_dir (str): The directory to analyze.
        exclude_patterns (List[str]): A list of file patterns to exclude.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                               represents a file and its permissions.
    """
    file_permissions_data = []
    try:
        spec = PathSpec.from_lines("gitwildcard", exclude_patterns)
        for root, _, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, source_dir)

                # Exclude files based on patterns
                if spec.match_file(relative_path):
                    logging.debug(f"Excluding file: {file_path}")
                    continue

                permissions = get_file_permissions(file_path)
                if permissions:
                    file_permissions_data.append(
                        {"file_path": relative_path, "permissions": permissions}
                    )
    except OSError as e:
        logging.error(f"Error walking directory {source_dir}: {e}")
        return []  # Return empty list to indicate failure.
    return file_permissions_data


def render_template(
    template_file: str, data: List[Dict[str, Any]]
) -> str:
    """
    Renders a Jinja2 template with the given data.

    Args:
        template_file (str): Path to the Jinja2 template file.
        data (List[Dict[str, Any]]): The data to pass to the template.

    Returns:
        str: The rendered template as a string.
    """
    try:
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.dirname(template_file)),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
        )
        template = env.get_template(os.path.basename(template_file))
        rendered_template = template.render(files=data)
        return rendered_template
    except jinja2.exceptions.TemplateError as e:
        logging.error(f"Error rendering template {template_file}: {e}")
        return None


def write_output(
    output_file: str, data: str, output_format: str
) -> None:
    """
    Writes the data to the output file in the specified format.

    Args:
        output_file (str): Path to the output file.
        data (str): The data to write.
        output_format (str): The format of the output (json or yaml).
    """
    try:
        if output_format == "json":
            try:
                json_data = json.loads(data)  # Validate JSON before writing
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON data: {e}")
                return

            with open(output_file, "w") as f:
                json.dump(json_data, f, indent=4)
        elif output_format == "yaml":
            try:
                import yaml
            except ImportError:
                logging.error(
                    "PyYAML is not installed. Please install it to use YAML output format."
                )
                return
            try:
                yaml_data = yaml.safe_load(data)
            except yaml.YAMLError as e:
                logging.error(f"Invalid YAML data: {e}")
                return

            with open(output_file, "w") as f:
                yaml.dump(yaml_data, f, indent=2)
        else:
            logging.error(f"Invalid output format: {output_format}")
            return

        logging.info(f"Successfully wrote output to {output_file}")

    except OSError as e:
        logging.error(f"Error writing to file {output_file}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")


def main() -> None:
    """
    Main function to execute the permission template generator.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    # Input validation
    if not os.path.isdir(args.source_dir):
        logging.error(f"Source directory {args.source_dir} does not exist.")
        sys.exit(1)

    if not os.path.isfile(args.template_file):
        logging.error(f"Template file {args.template_file} does not exist.")
        sys.exit(1)

    # Core functionality
    permissions_data = analyze_directory_permissions(
        args.source_dir, args.exclude_patterns
    )

    if not permissions_data:
        logging.warning("No permissions data collected.  Check source directory and exclude patterns.")
        # Decide whether to exit or continue with empty data based on requirements
        # sys.exit(0)  # Exit if no data is collected.

    rendered_template = render_template(args.template_file, permissions_data)

    if rendered_template is None:
        sys.exit(1)  # Exit if template rendering failed

    write_output(args.output_file, rendered_template, args.output_format)


if __name__ == "__main__":
    main()