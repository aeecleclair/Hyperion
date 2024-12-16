if __name__ == "__main__":
    from pathlib import Path

    from jinja2 import Environment, FileSystemLoader

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

    # Templates rendering
    # URL are set to MyECL only to test that the links are working properly
    template_account_exists_mail = env.get_template("account_exists_mail.html")
    html_account_exists_mail = template_account_exists_mail.render()
    file_account_exists_mail = directory / Path("test_account_exists_mail.html")
    file_account_exists_mail.touch(exist_ok=True)
    with file_account_exists_mail.open(mode="w") as f:
        f.write(html_account_exists_mail)

    template_activation_mail = env.get_template("activation_mail.html")
    html_activation_mail = template_activation_mail.render(
        calypsso_activate_url="https://myecl.fr",
    )
    file_activation_mail = directory / Path("test_activation_mail.html")
    file_activation_mail.touch(exist_ok=True)
    with file_activation_mail.open(mode="w") as f:
        f.write(html_activation_mail)

    template_migration_mail = env.get_template("migration_mail.html")
    html_migration_mail = template_migration_mail.render(
        migration_link="https://myecl.fr",
    )
    file_migration_mail = directory / Path("test_migration_mail.html")
    file_migration_mail.touch(exist_ok=True)
    with file_migration_mail.open(mode="w") as f:
        f.write(html_migration_mail)

    template_migration_mail_already_used = env.get_template(
        "migration_mail_already_used.html",
    )
    html_migration_mail_already_used = template_migration_mail_already_used.render()
    file_migration_mail_already_used = directory / Path(
        "test_migration_mail_already_used.html",
    )
    file_migration_mail_already_used.touch(exist_ok=True)
    with file_migration_mail_already_used.open(mode="w") as f:
        f.write(html_migration_mail_already_used)

    template_reset_mail = env.get_template("reset_mail.html")
    html_reset_mail = template_reset_mail.render(calypsso_reset_url="https://myecl.fr")
    file_reset_mail = directory / Path("test_reset_mail.html")
    file_reset_mail.touch(exist_ok=True)
    with file_reset_mail.open(mode="w") as f:
        f.write(html_reset_mail)

    template_reset_mail_does_not_exist = env.get_template(
        "reset_mail_does_not_exist.html",
    )
    html_reset_mail_does_not_exist = template_reset_mail_does_not_exist.render(
        calypsso_register_url="https://myecl.fr",
    )
    file_reset_mail_does_not_exist = directory / Path(
        "test_reset_mail_does_not_exist.html",
    )
    file_reset_mail_does_not_exist.touch(exist_ok=True)
    with file_reset_mail_does_not_exist.open(mode="w") as f:
        f.write(html_reset_mail_does_not_exist)
