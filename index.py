from dotenv import load_dotenv
load_dotenv()
import os
import shutil
from git import Repo
import pygments
from pygments.lexers import get_lexer_by_name
import openai

openai.api_key = os.getenv('OPENAI_API_KEY')

def download_github_repo(repo_url, local_dir="target_repos"):
    repo_name = repo_url.split('/')[-1]
    full_local_path = os.path.join(local_dir, repo_name)
    if os.path.exists(full_local_path):
        shutil.rmtree(full_local_path)
    os.makedirs(full_local_path, exist_ok=True)
    Repo.clone_from(repo_url, full_local_path)

def read_and_tokenize_code_files(local_dir="target_repos"):
    lexer = get_lexer_by_name("python", stripall=True)
    tokens = []
    for repo in os.listdir(local_dir):
        repo_path = os.path.join(local_dir, repo)
        for subdir, dirs, files in os.walk(repo_path):
            for file in files:
                if file.endswith('.py'):
                    with open(subdir + '/' + file, 'r') as f:
                        code = f.read()
                        file_tokens = list(pygments.lex(code, lexer))
                        tokens.extend(file_tokens)
    return tokens

def ask_gpt4_about_code(code_tokens, question, past_conversation=""):
    # Combine all code tokens and the question into a single text
    code_text = ' '.join(token[1] for token in code_tokens)
    prompt = f"The code is:\n{code_text}\n\n{past_conversation}{question}"

    # Call GPT-4 API to get a response to the question about the code
    response = openai.Completion.create(engine="text-davinci-003", prompt=prompt, max_tokens=1000)

    return response.choices[0].text.strip()

def prompt_user():
    repo_url = input("Enter the GitHub repository URL to target: ")
    download_github_repo(repo_url, './target_repos')
    code_tokens = read_and_tokenize_code_files('./target_repos')
    past_conversation = ""
    while True:
        question = input("What would you like to know about this repository? ")
        answer = ask_gpt4_about_code(code_tokens, question, past_conversation)
        print("\n>> GPT-4's answer: ", answer)

        past_conversation += f"User: {question}\nGPT-4: {answer}\n"

prompt_user()