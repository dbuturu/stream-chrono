import nox


@nox.session
def tests(session):
    session.install("pytest", "ffmpeg-python")
    session.run("pytest", "tests", env={"PYTHONPATH": "src"})


@nox.session
def lint(session):
    """Run linting with flake8."""
    session.install("flake8")
    session.run(
        "flake8",
        "--max-line-length=127",
        "--ignore=E203,E266,E501,W503",
        "chronostreamer",
        "tests",
    )


@nox.session
def build(session):
    """Build the package using pypa/build."""
    session.install("build")
    session.run("python", "-m", "build")


@nox.session
def install(session):
    """Install the package using pypa/installer."""
    session.install("build", "installer")  # Ensure installer is available
    session.run("python", "-m", "installer", "dist/*.whl")
