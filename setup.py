"""Setup script for DevOps LLM Agent CLI."""

from setuptools import setup, find_packages

setup(
    name="devops-agent-cli",
    version="1.0.0-beta",
    description="CLI tool for DevOps LLM Agent",
    author="DevOps Team",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.0",
        "httpx>=0.25.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "devops-agent=apps.cli.main:cli",
            "dagent=apps.cli.main:cli",
        ],
    },
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: System :: Systems Administration",
        "Programming Language :: Python :: 3.11",
    ],
)
