"""
Setup script for create_env package
"""

from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='create_env',
    version='0.0.1',
    author='Chandmare, Kunal',
    description='Scans Python source files and creates deterministic dependency manifests',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/chandmare/chandmare_ai_agents',
    packages=find_packages(),
    package_data={
        'create_env': ['package_name_mapping.json'],
    },
    include_package_data=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'create_env=create_env.cli:main',
        ],
    },
)

