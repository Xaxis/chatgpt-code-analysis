from dotenv import load_dotenv
load_dotenv()
import os
import shutil
from git import Repo
import pygments
from pygments.lexers import get_lexer_for_filename, guess_lexer, get_lexer_by_name
from pygments.formatters import TerminalFormatter
from termcolor import colored
import fnmatch
import openai

openai.api_key = os.getenv('OPENAI_API_KEY')

def highlight_code(code_string):
    lexer = get_lexer_by_name("python")
    formatter = TerminalFormatter()
    highlighted_code = pygments.highlight(code_string, lexer, formatter)
    return highlighted_code

def download_github_repo(repo_url, local_dir="target_repos"):
    repo_name = repo_url.split('/')[-1]
    full_local_path = os.path.join(local_dir, repo_name)
    if os.path.exists(full_local_path):
        shutil.rmtree(full_local_path)
    os.makedirs(full_local_path, exist_ok=True)
    Repo.clone_from(repo_url, full_local_path)

def read_and_tokenize_all_files(repo_path, ignore=None):
    if ignore is None:
        ignore = []
    structured_tokens = []
    for subdir, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pattern) for pattern in ignore)]
        for file in files:
            if any(fnmatch.fnmatch(file, pattern) for pattern in ignore):
                continue
            file_path = os.path.join(subdir, file)
            try:
                lexer = get_lexer_for_filename(file_path)
            except pygments.util.ClassNotFound:
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                    lexer = guess_lexer(content)
                except:
                    continue
            with open(file_path, 'r') as f:
                code = f.read()
                file_tokens = list(pygments.lex(code, lexer))
                structured_tokens.append({
                    'repo': repo_path.split('/')[-1],
                    'file_path': file_path,
                    'tokens': file_tokens
                })
    return structured_tokens

def ask_gpt4_about_code(structured_tokens, question, past_conversation="", max_tokens=1000):
    code_text = ""
    for file_data in structured_tokens:
        tokens = ' '.join(token[1] for token in file_data['tokens'])
        code_text += f"In the file '{file_data['file_path']}' of repo '{file_data['repo']}', the code is:\n{tokens}\n\n"
    prompt = f"{code_text}{past_conversation}{question}"
    response = openai.Completion.create(engine="text-davinci-003", prompt=prompt, max_tokens=max_tokens)
    return response.choices[0].text.strip()

def prompt_user():
    while True:

        # Get repo url
        repo_url = input(colored("\n>> Enter GitHub repository URL [https://github.com/Xaxis/chatgpt-code-analysis]: ", "green"))
        repo_url = repo_url if repo_url else "https://github.com/Xaxis/chatgpt-code-analysis"
        download_github_repo(repo_url, './target_repos')
        repo_name = repo_url.split('/')[-1]
        repo_path = os.path.join('./target_repos', repo_name)
        code_tokens = read_and_tokenize_all_files(
            repo_path,
            ["*.txt", "temp", ".git", "*.iml", ".idea", ".gitignore", "*.md", "*.json", "*.yml", "*.yaml", "*.xml", "*.gradle", "*.properties"]
        )

        # Get max_tokens
        max_tokens = input(colored("\n>> Enter 'max_tokens' value [1000]: ", "green"))
        max_tokens = int(max_tokens) if max_tokens.isdigit() else 1000

        # Start conversation
        past_conversation = ""
        while True:
            question = input(colored("\n>> What would you like to know? ", "green"))
            answer = ask_gpt4_about_code(code_tokens, question, past_conversation, max_tokens)

            # Check answer for code blocks to format
            if "```" in answer:
                start = answer.index("```") + 3
                end = answer.rindex("```")
                code_block = answer[start:end].strip()
                highlighted_code = highlight_code(code_block)
                answer = answer.replace(code_block, highlighted_code)

            # Print answer
            print("\n", answer)
            past_conversation += f"User: {question}\nGPT-4: {answer}\n"

            # Check if user wants to start a new session or continue asking questions
            new_session = input(colored("\n>> Would you like to start a new session? (y/n) ", "green"))
            if new_session.lower() == 'y':
                break

# Main program initialization
if __name__ == "__main__":
    prompt_user()