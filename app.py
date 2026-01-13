import json
import random
from openai import OpenAI
import streamlit as st
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="Streamlit Chat", page_icon="")
st.title("Interview Simulator")

if "setup_complete" not in st.session_state:
    st.session_state.setup_complete = False
if "user_message_count" not in st.session_state:
    st.session_state.user_message_count = 0
if "feedback_shown" not in st.session_state:
    st.session_state.feedback_shown = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_complete" not in st.session_state:
    st.session_state.chat_complete = False
if "question_count" not in st.session_state:
    st.session_state.question_count = 0
if "predefined_index" not in st.session_state:
    st.session_state.predefined_index = 0
if "question_plan" not in st.session_state:
    st.session_state.question_plan = []
if "question_plan_position" not in st.session_state:
    st.session_state.question_plan_position = ""
if "predefined_questions" not in st.session_state:
    st.session_state.predefined_questions = []
if "qa_pairs" not in st.session_state:
    st.session_state.qa_pairs = []

QUESTIONS_PATH = "questions.json"
MAX_QUESTIONS = 5
PREDEFINED_SOURCE = "predefined"
GENERATED_SOURCE = "generated"

def load_questions(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        st.error("Invalid questions.json format.")
        return {}

def build_predefined_pairs(pairs):
    return [
        {"question": pair["question"], "answer": pair["answer"]}
        for pair in pairs
        if pair["source"] == PREDEFINED_SOURCE
    ]

def format_feedback_text(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    formatted_lines = []
    bold_labels = ("Model answer:", "User answer:", "Missing areas:")
    for line in lines:
        if line.startswith("Overall score:"):
            if formatted_lines:
                formatted_lines.append("")
            formatted_lines.append(line)
            formatted_lines.append("")
            continue
        if line.startswith("Q") and ":" in line:
            if formatted_lines and formatted_lines[-1] != "":
                formatted_lines.append("")
            question_text = line.split(":", 1)[1].strip()
            if question_text:
                formatted_lines.append(question_text)
            continue
        for label in bold_labels:
            if line.startswith(label):
                line = line.replace(label, f"**{label}**", 1)
                break
        formatted_lines.append(line)
    return "<br>".join(formatted_lines)

def ask_question(source, client):
    if (
        source == PREDEFINED_SOURCE
        and st.session_state.predefined_index < len(st.session_state.predefined_questions)
    ):
        question = st.session_state.predefined_questions[st.session_state.predefined_index]
        st.session_state.predefined_index += 1
        with st.chat_message("assistant"):
            st.markdown(question)
        st.session_state.messages.append({"role": "assistant", "content": question})
        st.session_state.qa_pairs.append(
            {"question": question, "answer": "", "source": PREDEFINED_SOURCE}
        )
        return

    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        )
        question = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": question})
    st.session_state.qa_pairs.append(
        {"question": question, "answer": "", "source": GENERATED_SOURCE}
    )


def complete_setup():
   st.session_state.setup_complete = True

def show_feedback():
    st.session_state.feedback_shown = True


# only display the set of form if the set up is not complete
if not st.session_state.setup_complete:
    st.subheader("Personal information", divider="blue")

    if "name" not in st.session_state:
        st.session_state['name'] = ''
    if "experience" not in st.session_state:
        st.session_state['experience'] = ''
    if "skills" not in st.session_state:
        st.session_state['skills'] = ''

    st.session_state['name'] = st.text_input(label="Name", value=st.session_state['name'], placeholder="Enter your name")
    st.session_state['experience'] = st.text_area(label="Experience", value=st.session_state['experience'], placeholder="Describe your experience")
    st.session_state['skills'] = st.text_area(label="Skills", value=st.session_state['skills'], placeholder="List your skills")

    st.subheader('Company and Position', divider='blue')

    if "level" not in st.session_state:
        st.session_state['level'] = "Junior"
    if "position" not in st.session_state:
        st.session_state['position'] = "QA Manager"
    if "company" not in st.session_state:
        st.session_state['company'] = "Amazon"

    col1, col2 = st.columns(2)
    with col1:
        st.session_state['level'] = st.radio(
            "Choose level",
            key='visibility',
            options=['Junior', 'Mid-level', 'Senior'],
        )

    with col2:
        st.session_state['position'] = st.selectbox(
            "Choose a position",
            ("QA Manager", "Engineering Manager", "AWS Engineering Manager")
        )

    st.session_state['company'] = st.selectbox(
        "Choose a Company",
        ('Amazon', 'Google')
    )
    if st.button("Start interview", on_click=complete_setup):
        st.write("Setup complete, starting interview...")




# Start the interview
if st.session_state.setup_complete and not st.session_state.feedback_shown and not st.session_state.chat_complete:
    questions_by_position = load_questions(QUESTIONS_PATH)
    position_questions = questions_by_position.get(st.session_state["position"], [])
    use_predefined_questions = len(position_questions) > 0
    if use_predefined_questions:
        if st.session_state.question_plan_position != st.session_state["position"]:
            max_predefined = min(len(position_questions), MAX_QUESTIONS - 1)
            min_predefined = 1 if max_predefined > 0 else 0
            predefined_count = (
                random.randint(min_predefined, max_predefined)
                if max_predefined > 0
                else 0
            )
            st.session_state.predefined_questions = random.sample(
                position_questions, k=predefined_count
            )
            st.session_state.question_plan = (
                [PREDEFINED_SOURCE] * predefined_count
                + [GENERATED_SOURCE] * (MAX_QUESTIONS - predefined_count)
            )
            random.shuffle(st.session_state.question_plan)
            st.session_state.predefined_index = 0
            st.session_state.question_count = 0
            st.session_state.qa_pairs = []
            st.session_state.question_plan_position = st.session_state["position"]

    if use_predefined_questions:
        st.info("Answer the following questions...")
    else:
        st.info(
            """
            Start by introducing yourself...
            """
        )

    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = "gpt-4o"

    render_messages = True
    if not st.session_state.messages:
        st.session_state.messages = [{
            "role": "system", 
            "content": (f"You are a HR profes executive that interviews a candidate called {st.session_state['name']} " 
                        f"with experience {st.session_state['experience']} and skills {st.session_state['skills']}. "
                        f"You should interview them for the position {st.session_state['level']} {st.session_state['position']} "
                        f"at the company {st.session_state['company']}. "
                        "Ask only one interview question at a time. "
                        "Do not include sample answers, roleplay both sides, or provide a dialogue. "
                        "Output only the question text.")
        }]
        if use_predefined_questions and st.session_state.question_plan:
            source = st.session_state.question_plan[0]
            ask_question(source, client)
            st.session_state.question_count = 1
            render_messages = False

    if render_messages:
        for message in st.session_state.messages:
            if message["role"] != "system":
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

    if use_predefined_questions:
        if prompt := st.chat_input("Your answer:", max_chars=500):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            if st.session_state.qa_pairs:
                st.session_state.qa_pairs[-1]["answer"] = prompt

            if st.session_state.question_count < len(st.session_state.question_plan):
                source = st.session_state.question_plan[st.session_state.question_count]
                ask_question(source, client)
                st.session_state.question_count += 1
            else:
                st.session_state.chat_complete = True

            st.session_state.user_message_count += 1
    else:
        if st.session_state.user_message_count < MAX_QUESTIONS:
            if prompt := st.chat_input("Your answer:", max_chars=500):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                if st.session_state.user_message_count < MAX_QUESTIONS - 1:
                    with st.chat_message("assistant"):
                        stream = client.chat.completions.create(
                            model=st.session_state["openai_model"],
                            messages=[
                                {"role": m["role"], "content": m["content"]}
                                for m in st.session_state.messages
                            ],
                            stream=True,
                        )
                        response = st.write_stream(stream)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                
                st.session_state.user_message_count += 1
        
        if st.session_state.user_message_count >= MAX_QUESTIONS:
            st.session_state.chat_complete = True

if st.session_state.chat_complete and not st.session_state.feedback_shown:
    if st.button("Get feedback", on_click=show_feedback):
        st.write("Collecting feedback...")

# show the feedback screen
if st.session_state.feedback_shown:
    st.subheader("Feedback")

    predefined_pairs = build_predefined_pairs(st.session_state.qa_pairs)
    feedback_agent = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])
    feedback_model = st.session_state.get("openai_model", "gpt-4o")

    if predefined_pairs:
        qa_block = "\n".join(
            [
                f"Q{idx + 1}: {pair['question']}\nUser answer: {pair['answer'] or 'No answer provided.'}"
                for idx, pair in enumerate(predefined_pairs)
            ]
        )
        feedback_completion = feedback_agent.chat.completions.create(
            model=feedback_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an interview evaluator. For each question, write a concise model answer, "
                        "compare it to the user's answer, and highlight missing or weak areas. "
                        "Provide an overall score from 1 to 10. Do not ask any questions. "
                        "Use plain text with each label starting a new line. "
                        "Use this format:\n"
                        "Overall score: //Your score\n"
                        "Q1: //Question\n"
                        "Model answer: //Ideal answer\n"
                        "User answer: //Brief summary\n"
                        "Missing areas: //Gaps\n"
                        "Repeat Q sections for each question with a blank line between sections."
                    ),
                },
                {"role": "user", "content": f"Evaluate these Q&A pairs:\n{qa_block}"},
            ],
        )
        formatted_feedback = format_feedback_text(
            feedback_completion.choices[0].message.content
        )
        st.markdown(formatted_feedback, unsafe_allow_html=True)
    else:
        conversation_history = "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages]
        )
        feedback_completion = feedback_agent.chat.completions.create(
            model=feedback_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful tool that provides feedback on an applicant performance during the interview. "
                        "Before a feedback, give a score of one to 10 one being the lowest score and 10 being the highest score. "
                        "Follow this format:\n"
                        "Overall score: //Your score\n"
                        "Feedback: //here you put your feedback\n"
                        "Give only the feedback do not ask any additional questions."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "This is the interview you need to evaluate keep in mind that you are only a tool. "
                        f"You should not engage in any conversations: {conversation_history}"
                    ),
                },
            ],
        )
        formatted_feedback = format_feedback_text(
            feedback_completion.choices[0].message.content
        )
        st.markdown(formatted_feedback, unsafe_allow_html=True)

    if st.button("Restart interview", type='primary'):
        streamlit_js_eval(js_expressions='parent.window.location.reload()')
