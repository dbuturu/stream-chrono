import nox


@nox.session
def tests(session):
    session.install("ffmpeg-python")  # Add other dependencies as needed
    session.run("python", "-m", "unittest", "discover", "-s", "tests")


@nox.session
def lint(session):
    """Lint code with flake8."""
    session.install("flake8")  # Install linting tool
    session.run(
        "flake8",
        "--max-line-length=127",
        "--ignore=E203,E266,E501,W503",
    )


@nox.session
def build(session):
    """Build the package."""
    session.install("setuptools", "wheel")  # Install build tools
    session.run(
        "python", "setup.py", "sdist", "bdist_wheel"
    )  # Build source and wheel distributions


@nox.session
def upload(session):
    """Upload package to GitHub Packages."""
    session.install("twine")  # Install twine for uploading
    # Use the GitHub Packages repository URL for uploading
    session.run(
        "twine",
        "upload",
        "--repository-url",
        "https://upload.pypi.org/legacy/",
        "dist/*",
        env={
            "TWINE_USERNAME": "USERNAME",
            "TWINE_PASSWORD": "YOUR_GITHUB_PAT",
        },
    )
