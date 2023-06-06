from setuptools import setup, find_packages

setup(
    name='chatgpt-code-analysis',
    version='0.1.0',
    author='Wil Neeley',
    author_email='william.neeley@gmail.com',
    description='Simple tool for asking GPT4 questions about a repo held at a Github url.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/your-project-name',
    packages=find_packages(exclude=['tests']),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    python_requires='>=3.6',
    install_requires=[
        'python-dotenv',
        'GitPython',
        'Pygments',
        'inquirer',
        'openai',
        'tiktoken',
        'fnmatch',
        'textwrap'
    ],
    extras_require={
        'dev': [
            'pytest>=3.7',
        ],
    },
)
