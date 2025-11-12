"""
Setup configuration for Enterprise Multi-Agent Research System
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="enterprise-multi-agent-research",
    version="1.0.0",
    author="Aiman Younis",
    author_email="aimanyounises@gmail.com",
    description="A production-grade multi-agent AI system for autonomous enterprise research",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aimanyounises1/enterprise-multi-agent-research",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "monitoring": [
            "rich>=13.0.0",
            "loguru>=0.7.0",
        ],
        "caching": [
            "redis>=5.0.0",
            "cachetools>=5.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "enterprise-research=enterprise_multi_agent.enterprise_multi_agent:main",
            "mcp-server=mcp.enterprise_mcp_server:main",
        ],
    },
)
