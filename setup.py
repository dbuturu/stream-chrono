from setuptools import setup, find_packages

setup(
    name="chrono-streamer",  # Set to match your package name
    version="0.0.1",
    description="A client for audio processing, streaming, and recording",
    author="Daniel Kigen Buturu",
    author_email="dbuturu@gmail.com",
    packages=find_packages(),
    install_requires=[
        "ffmpeg-python",  # Add other dependencies as needed
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    url="https://github.com/dbuturu/stream-chrono",  # Your GitHub repo URL
)
