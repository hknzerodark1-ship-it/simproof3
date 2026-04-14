from setuptools import setup, find_packages

setup(
    name="repro-check",
    version="0.1.0",
    description="Deterministic reproducibility debugging for simulation pipelines",
    author="Hien Khac Nguyen",
    py_modules=["check_repro"],
    entry_points={
        "console_scripts": [
            "repro-check=check_repro:main",
        ],
    },
    install_requires=[],
    python_requires=">=3.8",
)
