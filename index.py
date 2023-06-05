from dotenv import load_dotenv
load_dotenv()
import os
import shutil
from git import Repo
import pygments
from pygments.lexers import get_lexer_for_filename, guess_lexer, get_lexer_by_name
from pygments.formatters import TerminalFormatter
import fnmatch
import inquirer
from inquirer import List, Checkbox, Text, prompt
import textwrap
import openai
import tiktoken

openai.api_key = os.getenv('OPENAI_API_KEY')

def highlight_code(code_string):
    try:
        lexer = pygments.lexers.guess_lexer(code_string)
    except pygments.util.ClassNotFound:
        lexer = pygments.lexers.get_lexer_by_name("text")
    formatter = TerminalFormatter()
    highlighted_code = pygments.highlight(code_string, lexer, formatter)
    return highlighted_code


def list_downloaded_repos(local_dir="target_repos"):
    if not os.path.exists(local_dir):
        return []
    else:
        return os.listdir(local_dir)


def download_github_repo(repo_url, local_dir="target_repos"):
    repo_name = repo_url.split('/')[-1]
    full_local_path = os.path.join(local_dir, repo_name)
    if os.path.exists(full_local_path):
        shutil.rmtree(full_local_path)
    os.makedirs(full_local_path, exist_ok=True)
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        raise EnvironmentError("Please set the GITHUB_TOKEN environment variable")
    repo_url = repo_url.replace('https://', f'https://{github_token}@')
    Repo.clone_from(repo_url, full_local_path)


def read_and_tokenize_all_files(repo_path, ignore=None):
    if ignore is None:
        ignore = []
    structured_tokens = []
    file_paths = []
    for subdir, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pattern) for pattern in ignore)]
        for file in files:
            if any(fnmatch.fnmatch(file, pattern) for pattern in ignore):
                continue
            file_path = os.path.join(subdir, file)
            file_paths.append(file_path)
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
    return structured_tokens, file_paths


def num_tokens_from_string(string, encoding_name):
    encoding = tiktoken.encoding_for_model(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def build_tokens_string(repo_name, structured_tokens, selected_files):
    token_string = ""
    for file_path in selected_files:
        file_data = next((data for data in structured_tokens if data['file_path'] == file_path), None)
        if file_data:
            tokens = ''.join(token[1] for token in file_data['tokens'])
            file_path = file_path.replace(f"./target_repos/{repo_name}/", "")
            token_string += f"File: '{file_path}', code:\n{tokens}\n\n"
    return token_string


def ask_gpt_question(messages, engine_id, max_tokens=4096):
    engine_target = "gpt-3.5-turbo" if engine_id == "GPT4" else "text-davinci-002"
    response = openai.ChatCompletion.create(
        # model=engine_target, # @TODO
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=max_tokens
    )
    return response['choices'][0]['message']['content'].strip()



def prompt_question_repo():
    downloaded_repos = list_downloaded_repos()
    repo_choices = ["Enter Repo URL"] + downloaded_repos
    repo_question = [
        List('selected_repo',
             message="Select a repo to analyze or enter a new URL",
             choices=repo_choices),
    ]
    selected_repo = prompt(repo_question)['selected_repo']
    return selected_repo


def prompt_question_repo_url(selected_repo):
    repo_url = None
    if selected_repo == "Enter Repo URL":
        repo_url_question = [
            Text('repo_url', message="Enter Repo URL"),
        ]
        repo_url = prompt(repo_url_question)['repo_url']
        repo_url = repo_url if repo_url else "https://github.com/Xaxis/chatgpt-code-analysis"
        download_github_repo(repo_url, './target_repos')
        repo_name = repo_url.split('/')[-1]
    else:
        repo_name = selected_repo
    return repo_name


def prompt_question_repo_files(file_paths):
    file_questions = [
        inquirer.Checkbox('selected_files',
                          message="Select files to analyze",
                          choices=["All files"] + file_paths,
                          default=["All files"]),
    ]
    selected_files = inquirer.prompt(file_questions)['selected_files']
    if "All files" in selected_files or not selected_files:
        selected_files = file_paths
    return selected_files


def prompt_question_engine():
    engine_question = [
        List('selected_engine', message="Select an engine", choices=["GPT4", "GPT3.5"], default="GPT4"),
    ]
    selected_engine = prompt(engine_question)['selected_engine']
    return selected_engine


def prompt_question_max_tokens():
    max_tokens_question = [
        List('max_tokens', message="Enter max tokens", choices=["256", "512", "1024", "2048", "4096"], default="1024"),
    ]
    max_tokens = prompt(max_tokens_question)['max_tokens']
    return int(max_tokens)


def prompt_question_loop():
    gpt_question = [
        List('selected_question', message="What now?", choices=["Ask question", "Start over", "Exit"], default="Ask question"),
    ]
    selected_question = inquirer.prompt(gpt_question)['selected_question']
    return selected_question


def prompt_user():
    while True:
        question_count = 0

        # Prompt user for repo
        selected_repo = prompt_question_repo()

        # Prompt user for repo URL if needed
        repo_name = prompt_question_repo_url(selected_repo)

        # Tokenize files in repo
        repo_path = os.path.join('./target_repos', repo_name)
        code_tokens, file_paths = read_and_tokenize_all_files(
            repo_path,
            [
                "*.txt", "temp", ".git", "*.iml", ".idea",
                ".gitignore", "*.json", "*.yml",
                "*.yaml", "*.xml", "*.gradle", "*.properties"
            ]
        )

        # Prompt user for files to analyze
        selected_files = prompt_question_repo_files(file_paths)

        # Prompt user for engine
        engine_id = prompt_question_engine()

        # Prompt user for max tokens
        max_tokens = prompt_question_max_tokens()

        # Build token string
        token_code_string = build_tokens_string(repo_name, code_tokens, selected_files)

        # Initialize messages
        messages = []

        # Start conversation
        while True:

            # Prompt user for next action
            selected_question = prompt_question_loop()
            if selected_question == "Ask question":
                question_question = [
                    Text('question', message="Enter a question"),
                ]
                selected_question = prompt(question_question)['question']
            if selected_question == "Exit":
                return
            if selected_question == "Start over":
                break

            # Prepare question, only sending code tokens on first question
            question_count += 1
            if question_count == 1:
                messages.append({
                    "role": "system",
                    "content": f"Analyze the following code that resides in the repo: '{repo_name}'. Wrap code blocks in response in triple backticks."
                })
                chunks = textwrap.wrap(token_code_string, max_tokens)
                for i, chunk in enumerate(chunks):
                    if i < len(chunks) - 1:
                        messages.append({
                            "role": "user",
                            "content": f"Code chunk: {chunk}"
                        })
                    else:
                        messages.append({
                            "role": "user",
                            "content": f"Final Code chunk: {chunk}"
                        })
            messages.append({
                "role": "user",
                "content": f"Question {question_count}: {selected_question}"
            })

            # Print all messages in list
            total_token_count = 0
            for message in messages:
                total_token_count += num_tokens_from_string(message['content'], "gpt-3.5-turbo")
                # print(f"\n\n{message['role']}: {message['content']}")

            # Output total token count
            print(f"Total tokens: {total_token_count}")

            # Ask GPT question
            answer = ask_gpt_question(messages, engine_id, max_tokens)

            # Check answer for code blocks to format
            if "```" in answer:
                start = answer.index("```") + 3
                end = answer.index("```", start)
                code_block = answer[start:end].strip()
                highlighted_code = highlight_code(code_block)
                highlighted_code = highlighted_code.replace("```", "")
                answer = answer[:start - 3] + highlighted_code + answer[end + 3:]

            # Print answer
            print("\n" + answer.strip() + "\n")


# Main program initialization
if __name__ == "__main__":
    prompt_user()
