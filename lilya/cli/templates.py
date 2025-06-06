from __future__ import annotations

import os
import shutil
import stat
from importlib import import_module
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from sayer import error, info

import lilya
from lilya.cli.base import BaseDirective
from lilya.cli.constants import TREAT_AS_PROJECT_DIRECTIVE
from lilya.cli.exceptions import DirectiveError


class TemplateDirective(BaseDirective):
    """
    Copy either a Lilya application layout template or a Lilya project
    layout.
    """

    rewrite_template_suffixes: Any = (
        (".py-tpl", ".py"),
        (".e-tpl", ""),
    )

    def handle(self, app_or_project: str, name: str, **options: Any) -> Any:
        self.app_or_project = app_or_project
        self.name = name
        self.a_or_an = "an" if app_or_project == "app" else "a"
        self.verbosity = options["verbosity"]
        self.with_deployment = options.get("with_deployment", False)
        self.deployment_folder_name = options.get("deployment_folder_name", None)
        self.with_structure = options.get("is_simple", False)

        if self.app_or_project not in TREAT_AS_PROJECT_DIRECTIVE:
            self.validate_name(name)
            top_dir = os.path.join(os.getcwd(), name)
        else:
            top_dir = os.path.join(os.getcwd(), self.deployment_folder_name)

        try:
            os.makedirs(top_dir)
        except FileExistsError:
            raise DirectiveError(f"{top_dir} already exists.") from None
        except OSError as e:
            raise DirectiveError(detail=str(e)) from e

        if self.app_or_project not in TREAT_AS_PROJECT_DIRECTIVE:
            base_name = f"{app_or_project}_name"
        else:
            base_name = "project_name"

        base_subdir = (
            f"{app_or_project}_template_simple"
            if not self.with_structure and self.app_or_project not in TREAT_AS_PROJECT_DIRECTIVE
            else f"{app_or_project}_template"
        )
        base_deployment = "deployment_template"

        context = {
            base_name: name,
            "lilya_version": self.get_version(),
            "project_secret": options.get("secret_key"),
            "deployment_folder": self.deployment_folder_name,
        }

        template_dir = os.path.join(lilya.__path__[0], "_internal/_templates", base_subdir)
        prefix_length = len(template_dir) + 1

        # Creates the project or application structure
        self.iterate_templates(
            top_dir=top_dir,
            prefix_length=prefix_length,
            name=name,
            base_name=base_name,
            app_or_project=app_or_project,
            template_dir=template_dir,
            context=context,
        )

        # Add deployment files to the project

        if self.with_deployment:
            template_dir = os.path.join(lilya.__path__[0], "_internal/_templates", base_deployment)
            prefix_length = len(template_dir) + 1
            self.iterate_templates(
                top_dir=top_dir,
                prefix_length=prefix_length,
                name=name,
                base_name=base_name,
                app_or_project=app_or_project,
                template_dir=template_dir,
                context=context,
                with_deployment=self.with_deployment,
                deployment_folder_name=self.deployment_folder_name,
            )

    def iterate_templates(
        self,
        top_dir: str,
        prefix_length: int,
        name: str,
        base_name: str,
        app_or_project: str,
        template_dir: str,
        context: dict[str, Any],
        with_deployment: bool = False,
        deployment_folder_name: str | None = None,
    ) -> None:
        """
        Iterates through a specific template directory and populates with the corresponding
        variables
        """
        for root, dirs, files in os.walk(template_dir):
            path_rest = root[prefix_length:]

            relative_dir = path_rest.replace(base_name, name)

            if with_deployment:
                relative_dir = f"{deployment_folder_name}/{relative_dir}"

            if relative_dir:
                target_dir = os.path.join(top_dir, relative_dir)
                os.makedirs(target_dir, exist_ok=True)

            for dirname in dirs[:]:
                if dirname.startswith(".") or dirname == "__pycache__":
                    dirs.remove(dirname)

            for filename in files:
                if filename.endswith((".pyo", ".pyc", ".py.class")):
                    continue

                old_path = os.path.join(root, filename)
                new_path = os.path.join(top_dir, relative_dir, filename.replace(base_name, name))
                project_dir = os.path.join(top_dir, relative_dir)
                template_name = filename
                for old_suffix, new_suffix in self.rewrite_template_suffixes:
                    if new_path.endswith(old_suffix):
                        new_path = new_path[: -len(old_suffix)] + new_suffix
                        template_name = template_name[: -len(old_suffix)] + new_suffix
                        break

                if os.path.exists(new_path):
                    raise DirectiveError(
                        f"{new_path} already exists. Overlaying {self.a_or_an} {app_or_project} into an existing "
                        "directory won't replace conflicting files."
                    )

                shutil.copyfile(old_path, new_path)
                if self.verbosity >= 2:
                    info(f"Creating {new_path}")
                try:
                    self.manage_template_variables(template_name, new_path, project_dir, context)
                    self.apply_umask(old_path, new_path)
                    self.make_file_writable(new_path)
                except OSError:
                    error(
                        f"Notice: Couldn't set permission bits on {new_path}. You're "
                        "probably using an uncommon filesystem setup. No "
                        "problem.",
                    )

    def manage_template_variables(
        self,
        template: str | Path,
        destination: str | Path,
        template_dir: str | Path,
        context: dict[str, Any],
    ) -> None:
        """
        Goes through every file generated and replaces the variables with the given
        context variables.
        """
        environment = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
        template = environment.get_template(template)  # type: ignore
        rendered_template = template.render(context)  # type: ignore
        if os.path.isfile(destination):
            os.unlink(destination)
        with open(destination, "w") as f:
            f.write(rendered_template)

    def validate_name(self, name: str | None, name_or_dir: str = "name") -> None:
        if name is None:
            raise DirectiveError(f"you must provide {self.a_or_an} {self.app_or_project} name")
        # Check it's a valid directory name.
        if not name.isidentifier():
            raise DirectiveError(
                f"'{name}' is not a valid {self.app_or_project} {type}. Please make sure the "
                "{type} is a valid identifier."
            )
        try:
            import_module(name)
        except ImportError:
            ...
        else:
            raise DirectiveError(
                f"'{name}' conflicts with the name of an existing project or folder "
                f"and cannot be used as {self.a_or_an} {self.app_or_project} {name_or_dir}. Please try "
                f"another {name_or_dir}."
            )

    def apply_umask(self, old_path: str | Path, new_path: str | Path) -> None:
        current_umask = os.umask(0)
        os.umask(current_umask)
        current_mode = stat.S_IMODE(os.stat(old_path).st_mode)
        os.chmod(new_path, current_mode & ~current_umask)

    def make_file_writable(self, filename: str) -> None:
        """
        Make sure that the file is writeable.
        Useful if our source is read-only.
        """
        if not os.access(filename, os.W_OK):
            st = os.stat(filename)
            new_permissions = stat.S_IMODE(st.st_mode) | stat.S_IWUSR
            os.chmod(filename, new_permissions)
