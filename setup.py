"""Setup file for libre-link-up-api-client-py"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="libre-link-up-api-client",
    version="0.1.0",
    author="",
    description="Python client for accessing Abbott's LibreLinkUp sharing service",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "pyyaml>=6.0.1",
        "python-dateutil>=2.8.2",
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "psycopg2-binary>=2.9.9",
        "pydantic>=2.5.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
    ],
)

