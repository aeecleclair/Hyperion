if __name__ == "__main__":
    from pathlib import Path

    from jinja2 import Environment, FileSystemLoader, meta

    # Please run from tests folder
    # Initialize environnement with templates
    path_to_file = Path(__file__)
    env = Environment(
        loader=FileSystemLoader(path_to_file.parents[1] / "assets/templates/"),
        autoescape=True,
    )

    # Create output directory if it doesnt exist
    directory = path_to_file.parents[0] / Path("jinja_test_outputs")
    directory.mkdir(exist_ok=True)

    for template in env.list_templates(
        filter_func=lambda x: x
        not in [
            "custom_mail_template.html",
            "base_email.html",
            "template.html",
            "README.md",
            "style.css",
        ],
    ):
        template_rendered = env.get_template(template)
        with Path.open(path_to_file.parents[1] / "assets/templates/" / template) as f:
            template_content = f.read()
        ast = env.parse(template_content)
        variables = meta.find_undeclared_variables(ast)
        html_rendered = template_rendered.render(
            {v: f"https://myecl.fr/{v}" for v in variables},
        )
        file_rendered = directory / Path(f"test_{template}")
        file_rendered.touch(exist_ok=True)
        with file_rendered.open(mode="w") as f:
            f.write(html_rendered)
