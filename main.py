import sys
import uuid
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QSplitter, QCheckBox
from PyQt5.QtGui import QPixmap
from openai import OpenAI
import os
from pydub import AudioSegment
from pydub.playback import play
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
import threading
import speech_recognition as sr
import random


client = OpenAI(api_key="")


# OpenAI Text-to-Speech
def generate_speech(input_text):
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=input_text
    )
    return response


# Function to send text to ChatGPT and get a response
def chat_with_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are girlfriend."},
            {"role": "user", "content": "Hey, how was your day?"},
            {"role": "assistant", "content": "My day was good, thank you for asking! How about yours?"},
            {"role": "user", "content": "It was okay, but I missed talking to you."},
            {"role": "assistant", "content": "Aww, I missed talking to you too!"},
            {"role": "user", "content": prompt}
        ],
    )
    return response.choices[0].message.content


class SpeechRecognitionThread(QThread):
    speech_recognized = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False

    def run(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            self.is_listening = True
            print("Listening...")
            while self.is_listening:
                try:
                    audio = self.recognizer.listen(source, timeout=3)
                    recognized_text = self.recognizer.recognize_google(audio)
                    self.speech_recognized.emit(recognized_text)
                except sr.WaitTimeoutError:
                    print("Timeout reached. Continue listening.")
                except sr.UnknownValueError:
                    print("Unable to recognize speech.")

    def stop_listening(self):
        self.is_listening = False

class Chatroom(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.audio_thread = None  # Store the audio thread
        self.audio_file_path = None  # Store the audio file path
        self.is_speech_recognition_enabled = False
        self.talking_images = ['talking.png', 'talking1.png', 'talking2.png']
        self.audio_ended = False
        self.dark_mode_enabled = False
        self.speech_thread = None

    def initUI(self):
        self.setWindowTitle('Mirai')
        self.setGeometry(100, 100, 800, 500)  # Increased width to accommodate image

        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        # Chat history and input area
        self.chat_layout = QVBoxLayout()
        self.layout.addLayout(self.chat_layout)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_layout.addWidget(self.chat_history)

        self.input_area = QTextEdit()
        self.input_area.setPlaceholderText("Type your message here...")

        # Adjusting the proportions using a splitter
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.chat_history)
        splitter.addWidget(self.input_area)
        # Set the sizes for the chat history and input area
        splitter.setSizes([int(3*self.height()/4), int(self.height()/4)])

        self.chat_layout.addWidget(splitter)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        self.chat_layout.addWidget(self.send_button)

        # Toggle button for speech recognition
        self.toggle_mic_button = QCheckBox("Enable Microphone")
        self.toggle_mic_button.stateChanged.connect(self.toggle_speech_recognition)
        self.chat_layout.addWidget(self.toggle_mic_button)

        # Toggle button for dark mode
        self.dark_mode_button = QCheckBox("Dark Mode")
        self.dark_mode_button.stateChanged.connect(self.toggle_dark_mode)
        self.chat_layout.addWidget(self.dark_mode_button)

        # Image display area
        self.image_layout = QVBoxLayout()
        self.layout.addLayout(self.image_layout)

        self.image_label = QLabel()
        self.image_layout.addWidget(self.image_label)

        # Load and display the PNG image
        pixmap = QPixmap('idle.png')  # Load your PNG image here
        self.image_label.setPixmap(pixmap)
        self.image_label.setScaledContents(True)

    def toggle_dark_mode(self, state):
        self.dark_mode_enabled = state == Qt.Checked
        self.update_dark_mode()

    def update_dark_mode(self):
        if self.dark_mode_enabled:
            # Change background color, text color, etc. for dark mode
            self.setStyleSheet("background-color: #333; color: white;")
        else:
            # Reset styles to default
            self.setStyleSheet("")

    def toggle_speech_recognition(self, state):
        if state == Qt.Checked:
            self.is_speech_recognition_enabled = True
            self.start_speech_recognition()
        else:
            self.is_speech_recognition_enabled = False
            self.stop_speech_recognition()

    def start_speech_recognition(self):
        if not self.speech_thread:
            self.speech_thread = SpeechRecognitionThread()
            self.speech_thread.speech_recognized.connect(self.handle_speech_recognition)
            self.speech_thread.start()

    def stop_speech_recognition(self):
        if self.speech_thread:
            self.speech_thread.stop_listening()
            self.speech_thread.wait()
            self.speech_thread = None

    def handle_speech_recognition(self, recognized_text):
        self.input_area.setPlainText(recognized_text)
        self.send_message()

    def send_message(self):
        self.audio_ended = False
        # Get user input
        user_input = self.input_area.toPlainText()

        # Display user message in chat history
        self.display_message("You:", user_input)

        # Get AI response
        ai_response = self.get_ai_response(user_input)

        # Display AI response in chat history
        self.display_message("Her:", ai_response)

        # Generate speech from AI response and play it
        self.generate_and_play_speech(ai_response)

        # Clear input area
        self.input_area.clear()

    def get_ai_response(self, user_input):
        # Call the function to chat with ChatGPT
        ai_response = chat_with_gpt(user_input)
        return ai_response

    def display_message(self, sender, message):
        self.chat_history.append(sender + " " + message)

    def generate_and_play_speech(self, text):
        # Load and display the opening PNG image
        opening_pixmap = QPixmap('opening.png')  # Load your opening PNG image here
        self.image_label.setPixmap(opening_pixmap)
        self.image_label.setScaledContents(True)

        # Generate speech from text
        audio_content = generate_speech(text)

        # Save the audio content to a unique file path
        self.audio_file_path = f"speech_{uuid.uuid4().hex}.mp3"
        with open(self.audio_file_path, 'wb') as f:
            f.write(audio_content.content)

        # Start a new thread to play the audio
        self.audio_thread = threading.Thread(target=self.play_audio)
        self.audio_thread.start()

        # Calculate the timing for image updates
        if self.audio_file_path:
            audio = AudioSegment.from_file(self.audio_file_path)
            total_duration = len(audio)
            switch_to_talking_time = int(total_duration * 0.05)  # Switch to talking PNG after 5% of audio duration
            switch_to_closing_time = int(total_duration * 0.95)  # Switch to closing PNG for last 5% of audio duration

            # Schedule image updates
            QTimer.singleShot(switch_to_talking_time, self.update_image_to_talking)
            QTimer.singleShot(switch_to_closing_time, self.update_image_to_closing)

    def play_audio(self):
        # Load the audio file using pydub
        audio = AudioSegment.from_file(self.audio_file_path)

        # Play the audio
        play(audio)

        # Clean up: remove the audio file
        if self.audio_file_path:
            os.remove(self.audio_file_path)

        # Set the audio ended flag to True
        self.audio_ended = True

        # Update the image to idle PNG after audio ends
        idle_pixmap = QPixmap('idle.png')
        self.image_label.setPixmap(idle_pixmap)
        self.image_label.setScaledContents(True)

    def update_image_to_talking(self):
        # Check if audio has ended
        if not self.audio_ended:
            # Select a random index for the talking PNG
            random_index = random.randint(0, len(self.talking_images) - 1)
            # Load and display the selected talking PNG
            talking_pixmap = QPixmap(self.talking_images[random_index])
            self.image_label.setPixmap(talking_pixmap)
            self.image_label.setScaledContents(True)
            # Generate a random delay between 1 and 2 seconds
            random_delay = random.uniform(1.0, 2.0)
            # Schedule the next update with the random delay
            QTimer.singleShot(int(random_delay * 1000), self.update_image_to_talking)

    def update_image_to_closing(self):
        # Load and display the closing PNG image
        closing_pixmap = QPixmap('opening.png')  # Load your closing PNG image here
        self.image_label.setPixmap(closing_pixmap)
        self.image_label.setScaledContents(True)


def main():
    app = QApplication(sys.argv)
    chatroom = Chatroom()
    chatroom.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
