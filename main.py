import json
import streamlit as st
from openai import OpenAI
from tenacity import retry, wait_random_exponential, stop_after_attempt
from colorama import Fore

# ------------------- INITIALISATION -----------------------

def getExistingInformation(db, list_name):
    if list_name not in db:
        return f'[], show this as an empty markdown table, with the heading center aligned. Table has only one column: {list_name}'
    return f'{[item for item in db[list_name]]}, show this as a markdown table, with the heading center aligned. Table has only one column: {list_name}'

def addNewInformation(db, list_name, item):
    if list_name not in db:
        db[list_name] = [item]
    else:
        db[list_name].append(item)
    return f'{item} added to {list_name}'

def removeInformation(db, list_name, item):
    if list_name not in db:
        return f'{item} does not exist in {list_name}, since the list is empty'
    try:
        db[list_name].remove(item)
    except:
        return f'Failed to delete {item} from {list_name}, item not found'

    return f'{item} deleted from {list_name}'

# tool list
type_of_request = [
    {
        "type": "function",
        "function": {
            "name": "get_existing_information",
            "description": "Get task/item from an existing list",
            "parameters": {
                "type": "object",
                "properties": {
                    "list_name": {
                        "type": "string",
                        "enum": ["shopping", "to-do"],
                        "description": "A type of list",
                    },
                },
                "required": ["list_name"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_new_information",
            "description": "Add task/item to an existing list",
            "parameters": {
                "type": "object",
                "properties": {
                    "list_name": {
                        "type": "string",
                        "enum": ["shopping", "to-do"],
                        "description": "A type of list",
                    },
                    "item": {
                        "type": "string",
                        "description": "Name of the task/item to add",
                    }
                },
                "required": ["list_name", "item"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_information",
            "description": "Remove existing information from a list",
            "parameters": {
                "type": "object",
                "properties": {
                    "list_name": {
                        "type": "string",
                        "enum": ["shopping", "to-do"],
                        "description": "A type of list",
                    },
                    "item": {
                        "type": "string",
                        "description": "Name of the item to remove",
                    }
                },
                "required": ["list_name", "item"],
            },
        }
    },
]

followup_tool = [
    {
        "type": "function",
        "function": {
            "name": "is_followup",
            "description": "Check if the prompt is a success or not",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["success", "followup"],
                        "description": "Success: operation completed, followup: expecting more information",
                    },
                    "item": {
                        "type": "string",
                        "description": "What item is success or to be followed up on",
                    }
                },
                "required": ["status", "item"],
            },
        }
    },
]

# default prompt
system_prompt =  {
    "role": "system", 
    "content": """You are a friendly journalling bot. 
        The user's request can be about the following:
        - adding new information, eg: "Remind me to buy eggs" "This is a task"
        - getting existing information, eg: "What is on my grocery list"
        - general talk about journals, eg: "How to write good to-do items", "What is a grocery list"
        If the user message is not related to journalling, tell the user that you can only cater to journalling tasks.
        Upon task completion, do NOT ask follow up questions such as "would you like to do anything more?"
        DO NOT ASSUME WHAT VALUES TO PLUG INTO THE FUNCTIONS. Ask for clarification if a user request is ambiguous"""}

# check if chatGPT response is expecting a follow up
followup_prompt = {
    "role": "system",
    "content" : """You are an intelligent bot. Given a message, you need to tell if the message denotes a success or is expecting a follow up from the user.""",
}


# init openAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = 'gpt-4o'

@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def chat_completion_request(messages, tools=None, tool_choice=None, model=st.session_state["openai_model"]):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
        )
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e
    

@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def check_follow_up(prompt, tool_choice=None, model=st.session_state["openai_model"]):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[followup_prompt]+ [{"role": "user", "content": prompt}],
            tools=followup_tool,
            tool_choice=tool_choice,
        )
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e


# ------------------- STREAMLIT -----------------------

with st.sidebar:
    st.markdown("# ✍️Logg.it")
    st.markdown("✨Your *personal* journal copilot.")
    st.markdown("The conversation is reset everytime the system thinks a task has been completed. The context shall persist to the LLM as long as it thinks it needs follow-up information, post which the tokens shall be discarded (marked with a *Context cleared* notification).")
    st.markdown("Start typing your journal items and the bot will auto-categorise them into the following categories:")
    st.markdown("""
    - Shopping list
    - To-do list
""")
    st.markdown("There is support for combining requests as well. For example:")
    st.markdown("`Add bread to my shopping list and show all lists`")
    st.markdown("will perform both actions in a single prompt!")

# Restore current session
if "messages" not in st.session_state:
    st.session_state.messages = [system_prompt]

if "messagesStore" not in st.session_state:
    st.session_state.messagesStore = [system_prompt]

for message in st.session_state.messagesStore:
    role = ""
    content = ""

    try:
        role = message["role"]
        content = message["content"]
    except:
        role = message.role
        content = message.content

    if role == "notification":
        st.markdown(content)
    elif role != "system" and role != "tool" and content != None:
        with st.chat_message(role):
            st.markdown(content)

    

if "db" not in st.session_state:
    st.session_state.db = {}

# input field
prompt = st.chat_input("What would you like to record today?")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messagesStore.append({"role": "user", "content": prompt})
    queryCompleteStatus = {}

    with st.chat_message("assistant"):
        response = chat_completion_request(st.session_state.messages, tools=type_of_request)
        st.session_state.messages.append(response.choices[0].message)
        st.session_state.messagesStore.append(response.choices[0].message)

        if (response.choices[0].finish_reason == 'tool_calls'):

            print(f"received {len(response.choices[0].message.tool_calls)} tool_calls")
            for i in range(len(response.choices[0].message.tool_calls)):
                fx = response.choices[0].message.tool_calls[i].function
                tool_call_id = response.choices[0].message.tool_calls[i].id
                args = json.loads(fx.arguments)

                if (fx.name == 'get_existing_information'):
                    result = getExistingInformation(st.session_state.db, args["list_name"])
                elif (fx.name == 'add_new_information'):
                    result = addNewInformation(st.session_state.db, args["list_name"], args["item"])
                elif (fx.name == "remove_information"):
                    result = removeInformation(st.session_state.db, args["list_name"], args["item"])
                
                st.session_state.messages.append({"role": "tool", "tool_call_id": tool_call_id, "name": fx.name, "content": result})
            print(st.session_state.db)
            response = chat_completion_request(st.session_state.messages)
            st.session_state.messages.append(response.choices[0].message)
            st.session_state.messagesStore.append(response.choices[0].message)
            

        st.markdown(response.choices[0].message.content)

        checkFollowUp = check_follow_up(response.choices[0].message.content)
        try:
            queryCompleteStatus = json.loads(checkFollowUp.choices[0].message.tool_calls[0].function.arguments)
        except:
            queryCompleteStatus["status"] = "followup"

        print(queryCompleteStatus)

    if "status" in queryCompleteStatus and queryCompleteStatus["status"] == "success":
        print(Fore.RED + "context has been reset, chat history cleared")
        print(Fore.RESET)
        st.session_state.messages = [system_prompt]
        st.markdown("*Context cleared...*")
        st.session_state.messagesStore.append({"role": "notification", "content": "*Context cleared...*"})
        