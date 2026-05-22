#!/usr/bin/env python3

import ollama
import pprint
import argparse
import json
import sys
import dotenv
import os
import requests
import json, re

parser = argparse.ArgumentParser()
parser.add_argument("-m", "--model", help="Set model to use", default="qwen2.5:7b")
parser.add_argument("-s", "--system", help="Set system prompt")
parser.add_argument("-c", "--context", help="Set num_ctx", type=int, default=20480)
parser.add_argument("-G", "--gpu", help="Set num_gpu", type=int, default=-1)
parser.add_argument("-T", "--temperature", help="Set temperature", type=int, default=1)
parser.add_argument("-t", "--tools", help="Set tools to use.  Use `list` to see available tools", default="add,get_operating_system")
parser.add_argument("-b", "--sandbox", help="Make the run_python_script tool use a sandbox", default=False, action="store_true")
parser.add_argument("-v", "--verbose", help="Show what's going on", action='count', default=1)
parser.add_argument("-q", "--quiet", help="Turn off debugging statements", dest='verbose', action='store_const', const=0)
parser.add_argument("-p", "--prompts", help="One or prompts", action='append', default=None)
parser.add_argument("-i", "--interactive", help="Enter interactive mode", action='store_true', default=False)
parser.add_argument("--test", help="Run canned prompts", action='store_true', default=False)
args = parser.parse_args()

all_tools = []

def tool(f):
        all_tools.append(f)
        return f

@tool
def add(l: list) -> float:
        """Adds 2 or more numbers and returns the result"""
        return sum(l)

@tool
def multiply(x: float, y: float) -> float:
        """Multiplies 2 numbers and returns the result"""
        return x * y

@tool
def subtract(x: float, y: float) -> float:
        """Substracts y from x and returns the result"""
        return x - y

@tool
def divide(x: float, y: float) -> float:
        """Divide x by y and returns the result"""
        return x / y

@tool
def count(l: list) -> int:
        """Counts the number of elements in a list and returns the result"""
        return len(l)

@tool
def power(x: float, y: float) -> float:
        """Raises x to the y power and returns the result"""
        return float(x) ** float(y)

@tool
def get_weather(country: str, city: str, unit: str) -> str:
        """ Returns the weather in the requested location """
        from bs4 import BeautifulSoup
        response = requests.get(f'https://www.timeanddate.com/weather/{country.replace(" ","-")}/{city.replace(" ","-")}')
        soup = BeautifulSoup(response.text, 'html.parser')
        r = []
        for paragraph in soup.find_all('p'):
            r.append(paragraph.text)
        return "\n".join(r)

@tool
def get_datetime() -> str:
        """
        Returns the current date and time as JSON data structure, in the format
            '{{"fulldate":"<fulldate>","date":"<date>","time":"<time>"}}'
        Time is in 24 hour format with the day starting at 00:00.
        """
        import datetime
        data = {
            "fulldate": datetime.datetime.now().strftime("%A, %B %d, %Y %H:%M %Z"),
            "date": datetime.datetime.now().strftime("%A, %B %d, %Y"),
            "time": datetime.datetime.now().strftime("%H:%M")
        }
        return json.dumps(data)

@tool
def get_operating_system() -> str:
        """
        Returns a string representing the operating system that
        the model is running on.
        """
        import platform
        return platform.platform()
    
@tool
def run_shell_command(command: str) -> str:
        """
        Execute a shell command and return its output as a string.
        """
        import subprocess

        try:
                # shell=True allows shell-specific features like pipes and redirections
                result = subprocess.run(
                        command,
                        shell=True,
                        check=True,  # Raises CalledProcessError if return code is non-zero
                        text=True,   # Return string instead of bytes
                        capture_output=True  # Capture stdout and stderr
                )
                return result.stdout.strip()
        except subprocess.CalledProcessError as e:
                # Include error message in the exception
                raise subprocess.CalledProcessError(
                        e.returncode,
                        e.cmd,
                        e.output,
                        f"Command failed with exit code {e.returncode}: {e.stderr}"
                )

# requires searxng instance at :5342
@tool
def web_search(query:str) -> str:
        """
        Searches the web using the supplied query and returns
        a JSON structure with a summary of the results.
        If the response from this tool doesn't provide the needed
        information, ignore it and inform the client.
        """
        import multiprocessing
        from collections import deque
        from bs4 import BeautifulSoup

        r = []
        response = requests.get("http://localhost:5342/search", params={"q":query,"format":"json"})
        if response.status_code != requests.codes.ok:
            return response
        results = response.json().get("results", [])
        if len(results) < 1:
            return "no results"
#    if x := response.json().get("infoboxes"):
#      r.append(x)

        taskq = multiprocessing.Queue()
        resultq = multiprocessing.Queue()

        def worker(id, taskq, resultq):
            while True:
                try:
                    url = taskq.get(timeout=1.0)
                    if url is None:
                        break
                    result = {"url":url,"status":0,"response":""}
                    try:
                        response = requests.get(url, timeout=30)
                        if response.status_code == requests.codes.ok:
                            s = []
                            soup = BeautifulSoup(response.content, 'html.parser')
                            for paragraph in soup.find_all('p'):
                                s.append(paragraph.text)
                            result["response"] = "\n".join(s)
                            result["status"] = requests.codes.ok
                    except Exception as e:
                        result["response"] = e
                    resultq.put(result)
                except multiprocessing.queues.Empty:
                    continue
                except Exception as e:
                    break

        workers = []
        for i in range(min(20, len(results))):
            p = multiprocessing.Process(
                    target=worker,
                    args=(i, taskq, resultq),
                    name=f"worker-{i}"
                )
            p.start()
            workers.append(p)

        urls = deque([result["url"] for result in results])
        tasks = len(results)
        for i in range(len(workers)):
            if urls:
                taskq.put(urls.popleft())
        while tasks:
            tasks -= 1
            result = resultq.get()
            if result["status"] == requests.codes.ok and len(result["response"]) > 10:
                r.append(result)
            if len(r) == 10:
                break
            if urls:
                taskq.put(urls.popleft())
        for _, p in enumerate(workers):
            p.terminate()
            p.join()
        return(r)

@tool
def read_file(filename:str) -> str:
        """
        Read the local file `filename` and return the contents.
        """
        with open(filename, "r") as f:
            return f.read()
        return ""

@tool
def http_get(url:str) -> str:
        """
        Retrieves a specific page from the internet.
        """
        return requests.get(url, timeout=10).text

@tool
def http_post(url:str, form:str) -> str:
        """
        Post a form to the specified url.
        """
        result = requests.post(url, data=form, timeout=10)
        if result.status_code == requests.codes.ok:
            return "success"
        return "fail"

@tool
def describe_contents_of_image_file(filename:str, query:str = None, model:str = None) -> str:
        """
        The file referenced by the `filename` argument is passed to
        a model which reads the contents of the file and returns
        a description of the image.

        Args:
            filename: name of the file to examine
            model: optional LLM
            query: optional query
        """
        f = filename
        if not (filename.startswith("/") or filename.startswith("./")):
            f = "./" + filename
        if not os.path.isfile(f):
            raise Exception(f"file '{filename}' does not exist")
        if not model:
            model = "gemma3:4b"
        if not query:
            query = 'describe this image'
        response = ollama.chat(
            model=model,
            messages=[{
                'role': 'user',
                'content': query,
                'images': [f]
            }]
        )
        return {"filename":filename, "description": response.message.content}

@tool
def get_current_directory() -> str:
        """
        Return the current working directory.
        """
        return run_shell_command("pwd")

@tool
def list_directory(directory: str) -> str:
        """
        Return the list of files in the named directory.
        """
        if directory != '~':
            directory = f"'{directory}'"
        return run_shell_command(f"ls {directory}")

@tool
def run_python_script(script: str) -> str:
        """
        Takes a python script as an argument, executes the script, and returns the results.
        The script must print results to stdout or save them in a file.
        If the 'run_python_script' tool returns no response, try again and make the script explicitly save the graph to a file.
        If the script requires modules, they should be added with "!pip install" commands.
        """
        if args.sandbox:
            return run_python_script_sandbox(script)
        return run_python_script_nosandbox(script)

@tool
def run_python_script_nosandbox(script: str) -> str:
        """
        Takes a python script as an argument, executes the script, and returns the results
        """
        from io import StringIO
        from contextlib import redirect_stdout

        f = StringIO()
        with redirect_stdout(f):
            try:
                ns = {}
                exec(script, globals(), ns)
                result = f.getvalue()
                if not result:
                    result = ns
            except Exception as e:
                result = str(e)
        return result

@tool
def run_python_script_sandbox(script: str) -> str:
        """
        Takes a python script as an argument, executes the script, and returns the results
        """
# pip install epicbox
# d=$(mktemp -d) && printf "FROM python:3.8-bookworm\nRUN pip install yfinance matplotlib\n" > $d/Dockerfile && docker build -f $d/Dockerfile -t python-sandbox $d && rm $d/Dockerfile && rmdir $d
        import epicbox
        import tempfile
        import base64

        epicbox.configure(
                profiles=[
                        epicbox.Profile('python', 'python-sandbox', network_disabled=False)
                ]
        )
        main = []
        scr = []
        timeout = 60
        for line in script.split("\n"):
            if line.startswith("# pip install"):
                timeout = timeout + 60
                main.append("pip install -qqq " + line[13:])
                continue
            if line.startswith("!pip install"):
                timeout = timeout + 60
                main.append("pip install -qqq " + line[12:])
                continue
            scr.append(line)
        main.append("""python3 ./script.py && { files=$(ls|egrep -v "^(main.sh|script.py)") ; [ -n "$files" ] && { comma="" ; echo '{"files": [' ; for i in $files ; do echo $comma'{ "name": "'$i'", "content": "'$(base64 -w0 "$i")'" }' ; comma=, ; done ; echo ']}' ; } ; : ; }""")
        files = [
                    { "name":"main.sh", "content": bytes("\n".join(main).encode()) },
                    { "name":"script.py", "content": bytes("\n".join(scr).encode()) },
        ]
        for f in files:
            print(f["name"])
            print(f["content"])
        result = epicbox.run("python", "sh main.sh", files=files, limits={"realtime":timeout,"cputime":timeout,"memory":1000})
        print(result)
        if result["timeout"]:
            return "script failed to start"
        if result["exit_code"] == 0:
            if len(result["stdout"]) == 0:
                return "There was no output from the script."
            try:
                j = json.loads(result["stdout"])
                res = []
                for f in j["files"]:
                    if "name" in f and "content" in f:
                        try:
                            content = base64.b64decode(f["content"])
                        except Exception as e:
                            content = f["content"]
                        with tempfile.NamedTemporaryFile(delete=False) as temp:
                            temp.write(content)
                            if f["name"].endswith(tuple([".jpg", ".jpeg", ".png", ".gif"])):
                                res.append(f'![{f["name"]}]({temp.name})')
                            else:
                                res.append(f'[{f["name"]}]({temp.name})')
                return "\n".join(res)
            except Exception as e:
                print(f"failed to load json: {e}")
                pass
            return result["stdout"]
        return result["stderr"]

@tool
def send_email(recipient:str, message:str, sender:str = None):
    """
    Sends an email message to the designated recipient.  The `sender`
    argument is optional and will be inferred from the auth details
    if not supplied.
    """
    import smtplib, ssl
    with smtplib.SMTP_SSL(os.getenv("SMTP_GATEWAY", "smtp.gmail.com"), 465, context=ssl.create_default_context()) as server:
        username = os.getenv("SMTP_USERNAME")
        password = os.getenv("SMTP_PASSWORD")
        if username and password:
                server.login(username, password)
        return server.sendmail(sender or username, recipient, message)

@tool
def post_to_bluesky(message:str):
    """
    Make a post to the bsky social network.
    """
    import atproto
    provider = os.getenv("BSKY_PROVIDER", "bsky.social")
    username = os.getenv("BSKY_USERNAME")
    password = os.getenv("BSKY_PASSWORD")
    if "." not in username:
        username = f"{username}.{provider}"
    client = atproto.Client()
    client.login(username, password)
    return client.send_post(message)

@tool
def get_recent_mastodon_posts(count:int = 5):
    """
    Get recent mastodon posts.
    """
    server = os.getenv("MASTODON_SERVER", "mastodon.social")
    return requests.get(f"https://{server}/api/v1/timelines/public?limit={count}").json()

@tool
def get_ip_address():
    """
    Returns the public IP address of this machine.
    """
    return requests.get("https://icanhazip.com").text

@tool
def get_location():
    """
    Returns the approximate location based on IP address.
    """
    return requests.get("https://mylocation.org", headers={"User-agent": "mozilla"}).text

all_tools_map = {t.__name__:t for t in all_tools}
tools = []

for tool in args.tools.split(","):
    match tool:
        case "all":
            tools = all_tools
        case "default":
            toolnames = [
                "add", "multiply", "subtract", "divide", "count", "power", 
                "get_weather", "get_datetime", "get_operating_system", 
                "run_shell_command", 
                "web_search", 
                "read_file", 
                "http_get", 
                "http_post", 
                # "describe_contents_of_image_file", 
                "get_current_directory", "list_directory", 
                "run_python_script", "run_python_script_nosandbox", "run_python_script_sandbox", 
            ]
            for tool in toolnames:
                if f := all_tools_map.get(tool):
                    tools.append(f)
        case "none":
            tools = []
        case "list":
            print("\n".join([f.__name__ for f in all_tools]))
            sys.exit(0)
        case _:
            if f := all_tools_map.get(tool):
                tools.append(f)
            
tools_map = {f.__name__:f for f in tools}

options = {
    "temperature":args.temperature,
    "num_ctx":args.context,
    "num_gpu":args.gpu,
}

import re
import json
import pprint

def extract_tool_call_from_text(content):
    """Fallback: parse tool call from raw text for models like Qwen"""
    content = content.strip()
    # Try <tool_call>...</tool_call> format
    match = re.search(r'<tool_call>(.*?)</tool_call>', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            return None
    # Try plain JSON object with "name" key
    try:
        data = json.loads(content)
        if "name" in data:
            return {"name": data["name"], "arguments": data.get("arguments", {})}
    except json.JSONDecodeError:
        pass
    return None


def chat(messages, prompt):
    messages.append({"role": "user", "content": prompt})
    print("== " + json.dumps(messages, indent=4, default=str) + " ==>LLM") if args.verbose > 1 else True

    last_tool_call = None  # track to detect infinite loops

    for _ in range(10):
        response = ollama.chat(model=args.model, options=options, messages=messages, tools=tools)
        content = response.message.content.strip()

        # Case 1: Devstral-style native tool_calls
        if response.message.tool_calls:
            messages.append({"role": "assistant", "content": content, "tool_calls": response.message.tool_calls})
            for tool_call in response.message.tool_calls:
                if tool_func := tools_map.get(tool_call.function.name):
                    print(f"calling {tool_call.function.name}({tool_call.function.arguments})") if args.verbose > 0 else True
                    try:
                        tool_output = tool_func(**tool_call.function.arguments)
                    except Exception as e:
                        print(e) if args.verbose > 1 else True
                        tool_output = e
                    if type(tool_output) == bytes:
                        tool_output = tool_output.decode()
                    messages.append({"role": "tool", "content": str(tool_output)})
            continue

        # Case 2: Qwen-style text tool call (JSON or <tool_call>)
        parsed = extract_tool_call_from_text(content)
        if parsed and (tool_func := tools_map.get(parsed["name"])):
            # Detect infinite loop — same call twice in a row means model ignores results
            call_signature = f"{parsed['name']}:{parsed['arguments']}"
            if call_signature == last_tool_call:
                print(f"Warning: model is looping on {parsed['name']}, forcing stop")
                break
            last_tool_call = call_signature

            print(f"calling {parsed['name']}({parsed['arguments']})") if args.verbose > 0 else True
            try:
                tool_output = tool_func(**parsed["arguments"])
            except Exception as e:
                print(e) if args.verbose > 1 else True
                tool_output = e
            if type(tool_output) == bytes:
                tool_output = tool_output.decode()
            print("tool_output:", tool_output) if args.verbose > 0 else True
            messages.append({"role": "assistant", "content": content, "tool_calls": None})
            messages.append({"role": "tool", "content": str(tool_output)})
            # Force a summarization prompt so Qwen doesn't just call again
            messages.append({"role": "user", "content": "Now summarize the result in plain text. Do not call any more tools."})
            continue

        # Case 3: <tool_call> tag but unparseable — warn and retry
        if '<tool_call>' in content:
            print(f"Warning: unparseable tool call: {content}")
            messages.append({"role": "user", "content": "Your tool call was malformed. Please try again with valid JSON."})
            continue

        # Case 4: Normal text response — done
        break

    print(f"{response.message.content}")
    return messages

dotenv.load_dotenv()

userprompt = ">>> " if sys.stdin.isatty() else ""

messages = [{"role":"system", "content":args.system}] if args.system else []

if args.test:
    args.prompts = [
        "what time is it?",
        "what is 10 ^ 1.34?",
        "what files are in the /tmp directory?",
        "what operating system are you running on?",
        "what is my ip address?",
        "what is my location?",
        "What's the weather where I am?",
        "What's the weather in Paris?",
        "count the number of files in the current directory",
        "when is sunrise in New Zealand tomorrow?",
        "summarize the contents of the file /etc/os-release",
        "what happened this week in AI?",
        "describe what's in ./filename.png",
        "What are the 3 most recent posts in mastodon?",
        "plot x^2",
    ]

if args.prompts:
    for p in args.prompts:
        print(f">>> {p}") if args.test else True
        messages = chat(messages, p)
if args.interactive or not args.prompts:
    while True:
        try:
            prompt = input(userprompt)
        except:
            print()
            break
        if prompt.startswith('"""'):
            long_prompt = prompt
            while True:
                try:
                    prompt = input("... ")
                except:
                    print()
                    break
                if prompt.startswith('"""'):
                    break
                long_prompt += prompt
            prompt = long_prompt
        if prompt.startswith('!'):
            os.system(prompt[1:])
            continue
        if prompt == "/bye":
            break
        if prompt == "/clear":
            messages = [{"role":"system", "content":args.system}] if args.system else []
            continue
        if prompt == "/dump":
            print(json.dumps(messages, indent=4, default=str))
            continue
        if prompt.startswith("/set"):
            cmd = prompt[5:].split()
            if cmd[0] == "parameter":
                options[cmd[1]] = float(cmd[2])
            if cmd[0] == "system":
                system = prompt.split(maxsplit=2)[2]
                messages.append({"role":"system", "content":system})
            continue
        messages = chat(messages, prompt)