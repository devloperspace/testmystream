import streamlit as st
import pandas as pd
import os
import base64
from datetime import datetime
from gtts import gTTS
import speech_recognition as sr
import plotly.express as px

# Constants and Paths
DATASET_PATH = "animal_dataset.csv"
RESULTS_FILE_PATH = "results.csv"

def ensure_results_file():
    if not os.path.exists(RESULTS_FILE_PATH):
        pd.DataFrame(columns=["child_id", "animal_name", "category", "attempt", "correct", "incorrect", "timestamp", "date"]).to_csv(RESULTS_FILE_PATH, index=False)

# Load dataset
try:
    animal_data = pd.read_csv(DATASET_PATH)
except FileNotFoundError:
    st.error(f"Dataset file '{DATASET_PATH}' not found.")
    st.stop()

# Utility Functions
def get_animal_details(category):
    """Fetch animals and details based on category."""
    return animal_data[animal_data["animal_category"].str.lower() == category.lower()]

def generate_audio(text):
    """Generate audio from text and return base64 string."""
    try:
        tts = gTTS(text, lang="en")
        audio_file_path = "temp_audio.mp3"
        tts.save(audio_file_path)

        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()
            b64_audio = base64.b64encode(audio_bytes).decode()

        os.remove(audio_file_path)
        return b64_audio
    except Exception as e:
        st.error(f"Error generating audio: {e}")
        return None

def recognize_speech():
    """Recognize speech using microphone input."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening... Please say the animal's name.")
        audio_data = recognizer.listen(source)
        try:
            return recognizer.recognize_google(audio_data).lower()
        except (sr.UnknownValueError, sr.RequestError) as e:
            st.error("Could not understand or request failed. Please try again.")
            return None

def save_to_csv(record):
    """Save a record to the CSV file."""
    ensure_results_file()
    df = pd.read_csv(RESULTS_FILE_PATH)
    df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    df.to_csv(RESULTS_FILE_PATH, index=False)

def load_results():
    """Load results from the CSV file."""
    ensure_results_file()
    return pd.read_csv(RESULTS_FILE_PATH)

# Pages
def home_page():
    st.title("Animal Sounds Learning Application")
    st.subheader("Choose a Category:")
    categories = ["Farm Animal", "Sea Creature", "Bird", "Wild Animal", "Jungle Animal"]
    for i, category in enumerate(categories):
        if st.button(category):
            st.session_state.selected_category = category.lower()
            st.session_state.page_index = i + 1
            break

def animal_page(category):
    st.title(f"{category.title()}")
    animals = get_animal_details(category)
    if animals.empty:
        st.error(f"No {category.lower()} found in the dataset.")
        return

    animal_names = animals["animal_name"].tolist()
    selected_animal_name = st.selectbox("Select an Animal:", animal_names)
    selected_animal = animals[animals["animal_name"] == selected_animal_name].iloc[0]

    try:
        st.image(selected_animal["url"], caption=selected_animal["animal_name"])
    except Exception:
        st.error(f"Failed to load image for {selected_animal_name}.")

    if st.button("Play Sound"):
        b64_audio = generate_audio(selected_animal_name)
        if b64_audio:
            st.markdown(f'<audio autoplay style="display:none;"><source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3"></audio>', unsafe_allow_html=True)

    if st.button("🎤 Try Saying Here"):
        recognized_text = recognize_speech()
        if recognized_text:
            is_correct = recognized_text == selected_animal_name.lower()
            st.session_state.test_attempts.append({"animal": selected_animal_name, "recognized_text": recognized_text, "is_correct": is_correct})

            if is_correct:
                st.success(f"Correct! You said '{selected_animal_name}'.")
            else:
                st.error(f"Incorrect. You said '{recognized_text}'. Try again.")

            record = {
                "child_id": st.session_state.child_id,
                "animal_name": selected_animal_name,
                "category": category,
                "attempt": 1,
                "correct": int(is_correct),
                "incorrect": int(not is_correct),
                "timestamp": datetime.now().timestamp(),
                "date": datetime.now().date()
            }
            save_to_csv(record)

def dashboard_page():
    st.title("Learning Dashboard")
    df = load_results()

    if df.empty:
        st.warning("No data available.")
        return

    time_filter = st.sidebar.radio("View Progress By", ["Daily", "Weekly", "Monthly"])
    categories = df['category'].unique()
    selected_category = st.sidebar.selectbox("Select Category", ["All"] + list(categories))

    if selected_category != "All":
        df = df[df['category'] == selected_category]

    if time_filter == "Daily":
        df['time_period'] = pd.to_datetime(df['date'])
    elif time_filter == "Weekly":
        df['time_period'] = pd.to_datetime(df['date']).dt.to_period('W').apply(lambda r: r.start_time)
    else:  # Monthly
        df['time_period'] = pd.to_datetime(df['date']).dt.to_period('M').apply(lambda r: r.start_time)

    trend_data = df.groupby('time_period')[['attempt', 'correct', 'incorrect']].sum().reset_index()

    total_attempts = df['attempt'].sum()
    total_correct = df['correct'].sum()
    total_incorrect = df['incorrect'].sum()

    st.subheader("Overall Statistics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Attempts", total_attempts)
    col2.metric("Total Correct", total_correct)
    col3.metric("Total Incorrect", total_incorrect)

    st.subheader(f"Trends in Attempts Over {time_filter.lower()}s")
    fig = px.line(trend_data, x='time_period', y=['attempt', 'correct', 'incorrect'],
                  labels={'value': 'Count', 'time_period': f'{time_filter}'},
                  title=f"{time_filter}-Wise Trends")
    st.plotly_chart(fig)

# Session State Initialization
if "page_index" not in st.session_state:
    st.session_state.page_index = 0
if "test_attempts" not in st.session_state:
    st.session_state.test_attempts = []
if "child_id" not in st.session_state:
    st.session_state.child_id = 1

pages = [home_page, lambda: animal_page("farm animal"), lambda: animal_page("sea creature"),
         lambda: animal_page("bird"), lambda: animal_page("wild animal"),
         lambda: animal_page("jungle animal"), dashboard_page]

pages[st.session_state.page_index]()

if st.session_state.page_index == 0 and st.button("Go to Dashboard"):
    st.session_state.page_index = 6
elif st.session_state.page_index > 0 and st.button("Back to Home"):
    st.session_state.page_index = 0
