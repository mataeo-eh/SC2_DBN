"""
Setup configuration for SC2 Replay Ground Truth Extraction Pipeline

This allows the package to be installed via pip:
    pip install -e .  # Development mode
    pip install .     # Standard installation
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README_SC2_PIPELINE.md"
if readme_file.exists():
    long_description = readme_file.read_text(encoding='utf-8')
else:
    long_description = "SC2 Replay Ground Truth Extraction Pipeline"

# Read requirements
requirements_file = Path(__file__).parent / "requirements_extraction.txt"
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text().splitlines()
        if line.strip() and not line.startswith('#')
    ]
else:
    requirements = [
        'pandas>=2.0.0',
        'pyarrow>=12.0.0',
        'numpy>=1.24.0',
    ]

setup(
    name="sc2-replay-extractor",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Extract ground truth game state from StarCraft II replays",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/local-play-bootstrap-main",
    packages=find_packages(include=['src_new', 'src_new.*']),
    package_dir={'': '.'},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Games/Entertainment :: Real Time Strategy",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-mock>=3.10.0',
            'black>=23.0.0',
            'isort>=5.12.0',
            'flake8>=6.0.0',
        ],
        'full': [
            'pysc2>=4.0.0',
            'jupyter>=1.0.0',
            'matplotlib>=3.5.0',
            'scikit-learn>=1.2.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'sc2-extract=src_new.pipeline.extraction_pipeline:main',
            'sc2-verify=verify_installation:main',
        ],
    },
    include_package_data=True,
    package_data={
        'src_new': ['*.md', '*.yaml', '*.json'],
    },
    zip_safe=False,
    keywords=[
        'starcraft',
        'sc2',
        'replay',
        'extraction',
        'machine-learning',
        'data-pipeline',
        'ground-truth',
        'game-state',
        'esports',
    ],
    project_urls={
        'Bug Reports': 'https://github.com/yourusername/local-play-bootstrap-main/issues',
        'Documentation': 'https://github.com/yourusername/local-play-bootstrap-main/tree/main/docs',
        'Source': 'https://github.com/yourusername/local-play-bootstrap-main',
    },
)
